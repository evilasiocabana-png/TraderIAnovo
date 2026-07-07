"""Servico de aplicacao para controle do replay."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from application.configuration_service import ConfigurationService
from application.research_service import ResearchData, ResearchService
from core.event_bus import EventBus
from core.event_logger import EventLogger, LoggedEvent
from core.events import (
    BACKTEST_FINISHED,
    DECISION_CREATED,
    FEATURE_SNAPSHOT_CREATED,
    NEW_CANDLE,
    ORDER_CREATED,
    ORDER_CLOSED,
    REGIME_ANALYSIS_CREATED,
    RESEARCH_ANALYSIS_CREATED,
    STRATEGY_SIGNAL_CREATED,
)
from core.decision_pipeline import DecisionPipeline
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from domain.contracts.market_snapshot import MarketSnapshot
from domain.market_state import MarketState
from market_data import HistoricalDataProvider, HistoricalDataset, MarketDataProvider
from market.candle_history import CandleHistory
from market.feature_engine import FeatureEngine, FeatureSnapshot
from market.feature_store import FeatureStore
from market.market_memory import MarketMemory
from market.regime_engine import RegimeAnalysis, RegimeEngine
from replay.replay_engine import ReplayEngine
from strategies.base import Strategy
from strategies.strategy_factory import StrategyFactory


class ReplayStatus(Enum):
    """Estados validos do replay."""

    EMPTY = "EMPTY"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"


@dataclass(frozen=True)
class ReplayData:
    """Dados de replay prontos para consumo da aplicacao."""

    current_index: int
    total_candles: int
    current_candle: Candle | None
    is_running: bool
    is_finished: bool
    status: ReplayStatus = ReplayStatus.EMPTY
    feature_snapshot: FeatureSnapshot | None = None
    regime_analysis: RegimeAnalysis | None = None
    research_data: ResearchData | None = None
    strategy_signal: StrategySignal | None = None
    decision_context: DecisionContext | None = None
    order_preview: ExecutionOrder | None = None
    paper_position: "PaperPosition | None" = None
    paper_trades_history: list["PaperPosition"] = field(
        default_factory=list
    )
    total_paper_trades: int = 0
    total_paper_result_points: float = 0.0
    wins: int = 0
    losses: int = 0
    paper_equity_curve: list[float] = field(default_factory=lambda: [0.0])
    current_equity_points: float = 0.0
    max_equity_points: float = 0.0
    min_equity_points: float = 0.0
    paper_metrics: "PaperMetrics" = field(default_factory=lambda: PaperMetrics())
    event_count: int = 0
    recent_events: list[LoggedEvent] = field(default_factory=list)
    candles_loaded: list[Candle] = field(default_factory=list)
    candles_processed: list[Candle] = field(default_factory=list)
    auto_run_enabled: bool = False
    replay_speed_seconds: float = 1.0
    active_strategy_name: str = "alpha001_iorb"
    active_strategy_label: str = "Alpha001 IORB"
    strategy_compatibility_warning: str = ""


@dataclass
class PaperPosition:
    """Posicao simulada em memoria para o replay."""

    side: str
    quantity: int
    entry_price: float
    stop: float
    target: float
    status: str = "OPEN"
    exit_price: float | None = None
    result_points: float = 0.0
    close_reason: str = ""


@dataclass(frozen=True)
class PaperMetrics:
    """Metricas das operacoes paper simuladas."""

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    gross_profit_points: float = 0.0
    gross_loss_points: float = 0.0
    net_profit_points: float = 0.0
    average_win_points: float = 0.0
    average_loss_points: float = 0.0
    profit_factor: float = 0.0
    current_drawdown_points: float = 0.0
    max_drawdown_points: float = 0.0
    peak_equity_points: float = 0.0


@dataclass
class ReplayService:
    """Controla o ReplayEngine sem expor a camada de replay a UI."""

    replay_engine: ReplayEngine = field(default_factory=ReplayEngine)
    candle_history: CandleHistory = field(default_factory=CandleHistory)
    feature_engine: FeatureEngine = field(default_factory=FeatureEngine)
    feature_store: FeatureStore = field(default_factory=FeatureStore)
    regime_engine: RegimeEngine = field(default_factory=RegimeEngine)
    market_memory: MarketMemory = field(default_factory=MarketMemory)
    research_service: ResearchService = field(default_factory=ResearchService)
    market_data_provider: MarketDataProvider = field(
        default_factory=HistoricalDataProvider
    )
    configuration_service: ConfigurationService = field(
        default_factory=ConfigurationService
    )
    strategy_factory: StrategyFactory = field(default_factory=StrategyFactory)
    strategy: Strategy = field(
        default_factory=lambda: StrategyFactory().create("alpha001_iorb")
    )
    active_strategy_name: str = "alpha001_iorb"
    alpha_minimum_range_size: float = 20.0
    alpha_minimum_volume: float = 1000.0
    decision_pipeline: DecisionPipeline = field(
        default_factory=DecisionPipeline
    )
    event_bus: EventBus = field(default_factory=EventBus)
    event_logger: EventLogger = field(default_factory=EventLogger)
    regime_analysis: RegimeAnalysis | None = None
    research_data: ResearchData | None = None
    strategy_signal: StrategySignal | None = None
    decision_context: DecisionContext | None = None
    order_preview: ExecutionOrder | None = None
    paper_position: PaperPosition | None = None
    paper_trades_history: list[PaperPosition] = field(default_factory=list)
    paper_equity_curve: list[float] = field(default_factory=lambda: [0.0])
    auto_run_enabled: bool = False
    replay_speed_seconds: float = 1.0
    status: ReplayStatus = ReplayStatus.EMPTY
    active_symbol: str = "WDO"
    active_timeframe: str = "1m"

    def __post_init__(self) -> None:
        """Conecta barramento e logger locais do replay."""
        self.replay_engine.event_bus = self.event_bus
        self._subscribe_logger()
        self.active_strategy_name = self._strategy_name(self.strategy)

    def list_available_strategies(self) -> list[str]:
        """Lista estrategias registradas para uso no Replay."""
        return self.strategy_factory.list_available()

    def get_active_strategy_name(self) -> str:
        """Retorna a estrategia atualmente executada pelo Replay."""
        return self.active_strategy_name

    def select_strategy(self, strategy_name: str) -> ReplayData:
        """Seleciona a estrategia que sera avaliada nos proximos candles."""
        normalized = strategy_name.strip().lower()
        if normalized not in self.list_available_strategies():
            raise ValueError(f"Estrategia desconhecida: {strategy_name}")
        if normalized != self.active_strategy_name:
            self.strategy = self.strategy_factory.create(normalized)
            self.active_strategy_name = normalized
            self.reset()
        return self.get_replay_data()

    def load_demo_candles(self) -> ReplayData:
        """Carrega candles demonstrativos em memoria."""
        self.active_symbol = "WDO"
        self.active_timeframe = "1m"
        return self.load_candles(self._demo_candles())

    def load_historical_data(self, source: object) -> ReplayData:
        """Carrega candles historicos usando o provider oficial de market data."""
        dataset = self.market_data_provider.load(source)
        return self.load_historical_dataset(dataset)

    def load_real_historical_dataset(
        self,
        symbol: str = "WDO",
        timeframe: str = "1m",
        period: str = "2025",
    ) -> ReplayData:
        """Carrega o Replay com dataset historico interno catalogado."""
        load_dataset = getattr(self.market_data_provider, "load_dataset", None)
        if not callable(load_dataset):
            return self._load_empty_dataset()
        dataset = load_dataset(symbol, timeframe, period)
        return self.load_historical_dataset(dataset)

    def load_historical_dataset(self, dataset: HistoricalDataset) -> ReplayData:
        """Carrega replay a partir de dataset historico ja resolvido."""
        if dataset.is_empty:
            return self._load_empty_dataset()
        self.active_symbol = dataset.symbol
        self.active_timeframe = dataset.timeframe
        return self.load_candles(dataset.candles)

    def load_historical_csv(self, path: object) -> ReplayData:
        """Compatibilidade com fachadas existentes de upload historico."""
        return self.load_historical_data(path)

    def load_candles(self, candles: list[Candle]) -> ReplayData:
        """Carrega candles externos preservando o fluxo padrao do replay."""
        self.replay_engine.load_candles(list(candles))
        self._clear_feature_pipeline()
        self.status = self._reset_status()
        return self.get_replay_data()

    def _load_empty_dataset(self) -> ReplayData:
        self.replay_engine.load_candles([])
        self._clear_feature_pipeline()
        self.status = ReplayStatus.EMPTY
        return self.get_replay_data()

    def start(self) -> ReplayData:
        """Inicia o replay."""
        if self.status in {ReplayStatus.EMPTY, ReplayStatus.FINISHED}:
            return self.get_replay_data()
        if self.replay_engine.current_index < 0:
            self.next_candle()
        if not self.replay_engine.is_finished:
            self.replay_engine.start()
            self.status = ReplayStatus.RUNNING
        return self.get_replay_data()

    def stop(self) -> ReplayData:
        """Para o replay."""
        self.replay_engine.stop()
        if self.status == ReplayStatus.RUNNING:
            self.status = ReplayStatus.PAUSED
        return self.get_replay_data()

    def reset(self) -> ReplayData:
        """Reinicia o replay."""
        self.replay_engine.reset()
        self._clear_feature_pipeline()
        self.status = self._reset_status()
        return self.get_replay_data()

    def next_candle(self) -> ReplayData:
        """Avanca para o proximo candle."""
        if self.status in {ReplayStatus.EMPTY, ReplayStatus.FINISHED}:
            return self.get_replay_data()
        candle = self.replay_engine.next_candle()
        if candle is not None:
            self._update_feature_pipeline(candle)
        if self.replay_engine.is_finished:
            self.status = ReplayStatus.FINISHED
            self.disable_auto_run()
        return self.get_replay_data()

    def enable_auto_run(self, speed_seconds: float) -> ReplayData:
        """Ativa o replay automatico em memoria."""
        self.replay_speed_seconds = max(float(speed_seconds), 0.0)
        if self.status not in {ReplayStatus.EMPTY, ReplayStatus.FINISHED}:
            self.auto_run_enabled = True
        return self.get_replay_data()

    def disable_auto_run(self) -> ReplayData:
        """Desativa o replay automatico."""
        self.auto_run_enabled = False
        return self.get_replay_data()

    def is_auto_run_enabled(self) -> bool:
        """Retorna se o replay automatico esta ativo."""
        return self.auto_run_enabled

    def get_replay_data(self) -> ReplayData:
        """Retorna o estado atual do replay como DTO de aplicacao."""
        state = self.replay_engine.get_state()
        return ReplayData(
            current_index=state.current_index,
            total_candles=state.total_candles,
            current_candle=state.current_candle,
            is_running=state.is_running,
            is_finished=state.is_finished,
            status=self.status,
            feature_snapshot=self.feature_store.latest(),
            regime_analysis=self.regime_analysis,
            research_data=self.research_data,
            strategy_signal=self.strategy_signal,
            decision_context=self.decision_context,
            order_preview=self.order_preview,
            paper_position=self.paper_position,
            paper_trades_history=list(self.paper_trades_history),
            total_paper_trades=len(self.paper_trades_history),
            total_paper_result_points=self._total_paper_result_points(),
            wins=self._paper_wins(),
            losses=self._paper_losses(),
            paper_equity_curve=list(self.paper_equity_curve),
            current_equity_points=self._current_equity_points(),
            max_equity_points=max(self.paper_equity_curve),
            min_equity_points=min(self.paper_equity_curve),
            paper_metrics=self._paper_metrics(),
            event_count=len(self.event_logger.get_events()),
            recent_events=self._recent_events(),
            candles_loaded=list(self.replay_engine.candles),
            candles_processed=self._candles_processed(),
            auto_run_enabled=self.auto_run_enabled,
            replay_speed_seconds=self.replay_speed_seconds,
            active_strategy_name=self.active_strategy_name,
            active_strategy_label=self._strategy_label(self.active_strategy_name),
            strategy_compatibility_warning=(
                self._strategy_compatibility_warning()
            ),
        )

    def _strategy_name(self, strategy: Strategy) -> str:
        return str(getattr(strategy, "nome", self.active_strategy_name)).strip().lower()

    def _strategy_label(self, strategy_name: str) -> str:
        labels = {
            "alpha001_iorb": "Alpha001 IORB",
            "alpha101": "Alpha101 Volume Momentum Breakout",
            "breakout": "Breakout",
            "pullback": "Pullback",
            "score_contexto": "Score Contexto",
            "smart_money": "Smart Money",
        }
        return labels.get(strategy_name, strategy_name)

    def _strategy_compatibility_warning(self) -> str:
        if (
            self.active_strategy_name == "alpha001_iorb"
            and self.active_symbol.upper() == "PETR4"
            and self.active_timeframe.lower() == "1d"
        ):
            return "Alpha001 IORB é incompatível com PETR4 1D. Esperado: WDO intraday."
        return ""

    def _reset_status(self) -> ReplayStatus:
        if self.replay_engine.candles:
            return ReplayStatus.READY
        return ReplayStatus.EMPTY

    def _update_feature_pipeline(self, candle: Candle) -> None:
        closed_position = self._update_paper_position(candle)
        self.candle_history.add_candle(candle)
        feature_snapshot = self.feature_engine.build(self.candle_history)
        self.feature_store.store(feature_snapshot)
        self._publish_feature_snapshot(feature_snapshot)
        market_snapshot = self._to_market_snapshot(candle, feature_snapshot)
        self.regime_analysis = self.regime_engine.analyze(
            market_snapshot
        )
        self._publish_regime_analysis(self.regime_analysis)
        self.research_data = self.research_service.analyze(
            feature_snapshot,
            self.regime_analysis,
            self.market_memory,
        )
        self._publish_research_analysis(self.research_data)
        self.strategy_signal = self._generate_strategy_signal(
            candle,
            feature_snapshot,
            market_snapshot,
        )
        self._publish_strategy_signal(self.strategy_signal)
        self.decision_context = self.decision_pipeline.processar(
            self.strategy_signal,
            market_snapshot,
            self._demo_risk_decision(),
        )
        self._publish_decision_context(self.decision_context)
        self.order_preview = self._build_order_preview(
            candle,
            self.decision_context,
        )
        if self.order_preview is not None and not closed_position:
            self._open_paper_position(self.order_preview)
        self.market_memory.remember(feature_snapshot, self.regime_analysis)

    def _clear_feature_pipeline(self) -> None:
        self.candle_history.clear()
        self.feature_store.clear()
        self.market_memory.clear()
        self.event_logger.clear()
        self.regime_analysis = None
        self.research_data = None
        self.strategy_signal = None
        self.decision_context = None
        self.order_preview = None
        self.paper_position = None
        self.paper_trades_history.clear()
        self.paper_equity_curve = [0.0]

    def _subscribe_logger(self) -> None:
        for event_name in self._replay_events():
            self.event_bus.subscribe(
                event_name,
                self._logger_handler(event_name),
            )

    def _logger_handler(self, event_name: str) -> Callable[[object], None]:
        def handle(payload: object) -> None:
            self.event_logger.handle_event(event_name, payload)

        return handle

    def _replay_events(self) -> tuple[str, ...]:
        return (
            NEW_CANDLE,
            BACKTEST_FINISHED,
            DECISION_CREATED,
            FEATURE_SNAPSHOT_CREATED,
            REGIME_ANALYSIS_CREATED,
            RESEARCH_ANALYSIS_CREATED,
            STRATEGY_SIGNAL_CREATED,
            ORDER_CREATED,
            ORDER_CLOSED,
        )

    def _recent_events(self) -> list[LoggedEvent]:
        return self.event_logger.get_events()[-10:]

    def _candles_processed(self) -> list[Candle]:
        if self.replay_engine.current_index < 0:
            return []
        end_index = self.replay_engine.current_index + 1
        return list(self.replay_engine.candles[:end_index])

    def _publish_feature_snapshot(self, snapshot: FeatureSnapshot) -> None:
        self.event_bus.publish(
            FEATURE_SNAPSHOT_CREATED,
            {"feature_snapshot": snapshot},
        )

    def _publish_regime_analysis(self, analysis: RegimeAnalysis) -> None:
        self.event_bus.publish(
            REGIME_ANALYSIS_CREATED,
            {"regime_analysis": analysis},
        )

    def _publish_research_analysis(self, research_data: ResearchData) -> None:
        self.event_bus.publish(
            RESEARCH_ANALYSIS_CREATED,
            {"research_data": research_data},
        )

    def _publish_strategy_signal(self, signal: StrategySignal) -> None:
        self.event_bus.publish(
            STRATEGY_SIGNAL_CREATED,
            {"strategy_signal": signal},
        )

    def _generate_strategy_signal(
        self,
        candle: Candle,
        feature_snapshot: FeatureSnapshot,
        market_snapshot: MarketSnapshot,
    ) -> StrategySignal:
        generator = getattr(self.strategy, "generate_signal", None)
        if callable(generator):
            return generator(
                candles=self._candles_processed(),
                market_snapshot=market_snapshot,
                current_price=candle.fechamento,
                minimum_range_size=self.alpha_minimum_range_size,
                minimum_volume=self.alpha_minimum_volume,
            )

        return self.strategy.analisar(
            self._to_market_state(candle, feature_snapshot)
        )

    def _publish_decision_context(self, context: DecisionContext) -> None:
        self.event_bus.publish(
            DECISION_CREATED,
            {"decision_context": context},
        )

    def _publish_order_created(self, paper_position: PaperPosition) -> None:
        self.event_bus.publish(
            ORDER_CREATED,
            {"paper_position": paper_position, "preview": True},
        )

    def _publish_order_closed(self, paper_position: PaperPosition) -> None:
        self.event_bus.publish(
            ORDER_CLOSED,
            {"paper_position": paper_position, "preview": True},
        )

    def _build_order_preview(
        self,
        candle: Candle,
        context: DecisionContext,
    ) -> ExecutionOrder | None:
        if not context.approved:
            return None
        if context.final_decision not in {"BUY", "SELL"}:
            return None
        configuration = self.configuration_service.get_configuration_data()
        entry_price = candle.fechamento
        return ExecutionOrder(
            side=context.final_decision,
            quantity=1,
            entry_price=entry_price,
            stop=self._order_stop(
                context.final_decision,
                entry_price,
                configuration.stop_points,
            ),
            target=self._order_target(
                context.final_decision,
                entry_price,
                configuration.target_points,
            ),
        )

    def _order_stop(
        self,
        side: str,
        entry_price: float,
        stop_points: float,
    ) -> float:
        if side == "BUY":
            return entry_price - stop_points
        return entry_price + stop_points

    def _order_target(
        self,
        side: str,
        entry_price: float,
        target_points: float,
    ) -> float:
        if side == "BUY":
            return entry_price + target_points
        return entry_price - target_points

    def _open_paper_position(self, order: ExecutionOrder) -> None:
        if self._has_open_paper_position():
            return
        self.paper_position = PaperPosition(
            side=order.side,
            quantity=order.quantity,
            entry_price=order.entry_price,
            stop=order.stop,
            target=order.target,
        )
        self._publish_order_created(self.paper_position)

    def _has_open_paper_position(self) -> bool:
        return (
            self.paper_position is not None
            and self.paper_position.status == "OPEN"
        )

    def _update_paper_position(self, candle: Candle) -> bool:
        if not self._has_open_paper_position():
            return False
        position = self.paper_position
        if position.side == "BUY":
            return self._update_buy_position(candle, position)
        return self._update_sell_position(candle, position)

    def _update_buy_position(
        self,
        candle: Candle,
        position: PaperPosition,
    ) -> bool:
        if candle.minima <= position.stop:
            self._close_paper_position(position.stop, "STOP")
            return True
        if candle.maxima >= position.target:
            self._close_paper_position(position.target, "TARGET")
            return True
        return False

    def _update_sell_position(
        self,
        candle: Candle,
        position: PaperPosition,
    ) -> bool:
        if candle.maxima >= position.stop:
            self._close_paper_position(position.stop, "STOP")
            return True
        if candle.minima <= position.target:
            self._close_paper_position(position.target, "TARGET")
            return True
        return False

    def _close_paper_position(
        self,
        exit_price: float,
        close_reason: str,
    ) -> None:
        position = self.paper_position
        if position is None:
            return
        position.status = close_reason
        position.exit_price = exit_price
        position.close_reason = close_reason
        position.result_points = self._position_result_points(position)
        self.paper_trades_history.append(position)
        self._update_paper_equity_curve(position.result_points)
        self._publish_order_closed(position)

    def _position_result_points(self, position: PaperPosition) -> float:
        if position.exit_price is None:
            return 0.0
        if position.side == "BUY":
            return position.exit_price - position.entry_price
        return position.entry_price - position.exit_price

    def _total_paper_result_points(self) -> float:
        return sum(trade.result_points for trade in self.paper_trades_history)

    def _update_paper_equity_curve(self, result_points: float) -> None:
        self.paper_equity_curve.append(
            self._current_equity_points() + result_points
        )

    def _current_equity_points(self) -> float:
        return self.paper_equity_curve[-1]

    def _paper_wins(self) -> int:
        return len(
            [
                trade
                for trade in self.paper_trades_history
                if trade.result_points > 0
            ]
        )

    def _paper_losses(self) -> int:
        return len(
            [
                trade
                for trade in self.paper_trades_history
                if trade.result_points < 0
            ]
        )

    def _paper_metrics(self) -> PaperMetrics:
        winners = self._paper_winner_results()
        losers = self._paper_loser_results()
        total_trades = len(self.paper_trades_history)
        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        return PaperMetrics(
            total_trades=total_trades,
            wins=len(winners),
            losses=len(losers),
            win_rate=self._win_rate(total_trades, len(winners)),
            gross_profit_points=gross_profit,
            gross_loss_points=gross_loss,
            net_profit_points=gross_profit - gross_loss,
            average_win_points=self._average(winners),
            average_loss_points=self._average(losers),
            profit_factor=self._profit_factor(gross_profit, gross_loss),
            current_drawdown_points=self._current_drawdown_points(),
            max_drawdown_points=self._max_drawdown_points(),
            peak_equity_points=max(self.paper_equity_curve),
        )

    def _paper_winner_results(self) -> list[float]:
        return [
            trade.result_points
            for trade in self.paper_trades_history
            if trade.result_points > 0
        ]

    def _paper_loser_results(self) -> list[float]:
        return [
            trade.result_points
            for trade in self.paper_trades_history
            if trade.result_points < 0
        ]

    def _win_rate(self, total_trades: int, wins: int) -> float:
        if total_trades == 0:
            return 0.0
        return wins / total_trades

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _profit_factor(
        self,
        gross_profit: float,
        gross_loss: float,
    ) -> float:
        if gross_loss == 0.0 and gross_profit > 0.0:
            return float("inf")
        if gross_loss == 0.0:
            return 0.0
        return gross_profit / gross_loss

    def _current_drawdown_points(self) -> float:
        return max(self.paper_equity_curve) - self._current_equity_points()

    def _max_drawdown_points(self) -> float:
        peak = self.paper_equity_curve[0]
        max_drawdown = 0.0
        for equity in self.paper_equity_curve:
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    def _demo_risk_decision(self) -> RiskDecision:
        return RiskDecision(
            allowed=True,
            reason="Replay de pesquisa. Operacao real nao autorizada.",
            max_contracts=1,
            risk_multiplier=1.0,
        )

    def _to_market_snapshot(
        self,
        candle: Candle,
        feature_snapshot: FeatureSnapshot,
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=self.active_symbol,
            datetime=candle.data,
            regime=self._snapshot_regime(feature_snapshot),
            volatility=feature_snapshot.average_range,
            liquidity=float(candle.volume),
            trend_strength=feature_snapshot.trend_strength,
            market_dna_score=0.0,
        )

    def _snapshot_regime(self, feature_snapshot: FeatureSnapshot) -> str:
        if feature_snapshot.direction == "SIDEWAYS":
            return "RANGE"
        return feature_snapshot.direction

    def _to_market_state(
        self,
        candle: Candle,
        feature_snapshot: FeatureSnapshot,
    ) -> MarketState:
        return MarketState(
            candle=candle,
            vwap=candle.fechamento,
            atr=feature_snapshot.average_range,
            pullback_pontos=0.0,
            horario=self._hour_from_candle(candle),
        )

    def _hour_from_candle(self, candle: Candle) -> int:
        try:
            return int(candle.data.split(" ")[1].split(":")[0])
        except (IndexError, ValueError):
            return 0

    def _demo_candles(self) -> list[Candle]:
        return [
            self._candle("2026-06-26 09:00", 5520.0, 5530.0, 5515.0, 5528.0),
            self._candle("2026-06-26 09:01", 5528.0, 5538.0, 5524.0, 5535.0),
            self._candle("2026-06-26 09:02", 5535.0, 5540.0, 5529.0, 5531.0),
            self._candle("2026-06-26 09:03", 5531.0, 5545.0, 5528.0, 5542.0),
            self._candle("2026-06-26 09:04", 5542.0, 5548.0, 5536.0, 5539.0),
        ]

    def _candle(
        self,
        data: str,
        abertura: float,
        maxima: float,
        minima: float,
        fechamento: float,
    ) -> Candle:
        return Candle(
            data=data,
            abertura=abertura,
            maxima=maxima,
            minima=minima,
            fechamento=fechamento,
            volume=1000,
        )
