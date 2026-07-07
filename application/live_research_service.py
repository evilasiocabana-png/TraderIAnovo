"""Servico live read-only para pesquisa quantitativa com candles MT5."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from application.mt5_market_data_service import (
    MT5IngestionSummary,
    MT5MarketDataService,
)
from application.research_service import ResearchData, ResearchService
from core.decision_pipeline import DecisionPipeline
from core.event_bus import EventBus
from core.events import (
    DECISION_CREATED,
    FEATURE_SNAPSHOT_CREATED,
    NEW_CANDLE,
    REGIME_ANALYSIS_CREATED,
    RESEARCH_ANALYSIS_CREATED,
    STRATEGY_SIGNAL_CREATED,
)
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from market.candle_history import CandleHistory
from market.feature_engine import FeatureEngine, FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import RegimeAnalysis, RegimeEngine
from research.live_experiment_runner import LiveExperimentRunner
from strategies.base import Strategy
from strategies.strategy_factory import StrategyFactory


@dataclass(frozen=True)
class LiveStrategyResult:
    """Resultado live read-only de uma estrategia registrada."""

    strategy_name: str
    strategy_signal: StrategySignal
    decision_context: DecisionContext


@dataclass(frozen=True)
class LiveResearchData:
    """Snapshot de pesquisa live pronto para consumo do Dashboard."""

    symbol: str
    timeframe: str
    current_candle: Candle
    feature_snapshot: FeatureSnapshot
    regime_analysis: RegimeAnalysis
    research_data: ResearchData
    market_snapshot: MarketSnapshot
    strategy_results: list[LiveStrategyResult]
    event_count: int
    ingestion_summary: MT5IngestionSummary | None = None


@dataclass(frozen=True)
class LiveResearchSignalRecord:
    """Sinal individual de uma estrategia durante a sessao live."""

    strategy_name: str
    decision: str
    confidence: float


@dataclass(frozen=True)
class LiveResearchSnapshotRecord:
    """Registro resumido de um processamento live mantido em memoria."""

    timestamp: str
    symbol: str
    timeframe: str
    decision: str
    confidence: float
    strategy_signals: int
    decision_contexts: int
    signals: list[LiveResearchSignalRecord] = field(default_factory=list)


@dataclass(frozen=True)
class LiveResearchSignalQuality:
    """Qualidade agregada dos sinais por estrategia."""

    strategy_name: str
    signal_count: int
    buy_count: int
    sell_count: int
    wait_count: int
    average_confidence: float
    last_decision: str


@dataclass(frozen=True)
class LiveResearchSessionSummary:
    """Resumo estatistico da sessao live mantida em memoria."""

    total_snapshots: int = 0
    buy_count: int = 0
    sell_count: int = 0
    wait_count: int = 0
    average_confidence: float = 0.0
    highest_confidence: float = 0.0
    lowest_confidence: float = 0.0
    last_decision: str = "N/D"
    last_timestamp: str = "N/D"


@dataclass
class LiveResearchService:
    """Executa a cadeia analitica live sem criar ordens."""

    mt5_market_data_service: MT5MarketDataService = field(
        default_factory=MT5MarketDataService
    )
    candle_history: CandleHistory = field(default_factory=CandleHistory)
    feature_engine: FeatureEngine = field(default_factory=FeatureEngine)
    regime_engine: RegimeEngine = field(default_factory=RegimeEngine)
    research_service: ResearchService = field(default_factory=ResearchService)
    market_memory: MarketMemory = field(default_factory=MarketMemory)
    strategy_factory: StrategyFactory = field(default_factory=StrategyFactory)
    decision_pipeline: DecisionPipeline = field(default_factory=DecisionPipeline)
    live_experiment_runner: LiveExperimentRunner = field(
        default_factory=LiveExperimentRunner
    )
    event_bus: EventBus = field(default_factory=EventBus)
    latest_data: LiveResearchData | None = None
    event_count: int = 0
    snapshot_history_limit: int = 20
    snapshot_history: list[LiveResearchSnapshotRecord] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.mt5_market_data_service.candle_history = self.candle_history
        self.mt5_market_data_service.event_bus = self.event_bus

    def ingest_from_mt5(
        self,
        symbol: str,
        timeframe: Any,
        count: int = 10,
    ) -> LiveResearchData | None:
        """Ingere candles MT5 e processa a cadeia live ate DecisionPipeline."""
        summary = self.mt5_market_data_service.ingest_candles(
            symbol,
            timeframe,
            count,
        )
        if summary.inserted_candles == 0:
            return None

        processed: LiveResearchData | None = None
        for candle in self.candle_history.last_n(summary.inserted_candles):
            processed = self.process_candle(
                candle,
                symbol=summary.symbol,
                timeframe=summary.timeframe,
                ingestion_summary=summary,
                publish_new_candle=False,
            )
        return processed

    def process_candle(
        self,
        candle: Candle,
        symbol: str = "UNKNOWN",
        timeframe: str = "UNKNOWN",
        ingestion_summary: MT5IngestionSummary | None = None,
        publish_new_candle: bool = True,
    ) -> LiveResearchData:
        """Processa um candle live recebido sem executar ordens."""
        if publish_new_candle:
            self.event_bus.publish(NEW_CANDLE, candle)
            self._record_event()
            self.candle_history.add_candle(candle)

        feature_snapshot = self.feature_engine.build(self.candle_history)
        self.event_bus.publish(FEATURE_SNAPSHOT_CREATED, feature_snapshot)
        self._record_event()

        market_snapshot = self._to_market_snapshot(
            candle,
            feature_snapshot,
            symbol,
        )
        regime_analysis = self.regime_engine.analyze(market_snapshot)
        self.event_bus.publish(REGIME_ANALYSIS_CREATED, regime_analysis)
        self._record_event()

        research_data = self.research_service.analyze(
            feature_snapshot,
            regime_analysis,
            self.market_memory,
        )
        self.event_bus.publish(RESEARCH_ANALYSIS_CREATED, research_data)
        self._record_event()

        strategy_results = self._run_registered_strategies(
            candle,
            feature_snapshot,
            market_snapshot,
            timeframe,
        )

        self.market_memory.remember(feature_snapshot, regime_analysis)
        self.latest_data = LiveResearchData(
            symbol=symbol,
            timeframe=timeframe,
            current_candle=candle,
            feature_snapshot=feature_snapshot,
            regime_analysis=regime_analysis,
            research_data=research_data,
            market_snapshot=market_snapshot,
            strategy_results=strategy_results,
            event_count=self.event_count,
            ingestion_summary=ingestion_summary,
        )
        self._remember_snapshot(self.latest_data)
        return self.latest_data

    def get_latest_data(self) -> LiveResearchData | None:
        """Retorna o ultimo snapshot live processado."""
        return self.latest_data

    def list_snapshot_history(self) -> list[LiveResearchSnapshotRecord]:
        """Retorna copia do historico live mantido somente em memoria."""
        return list(self.snapshot_history)

    def set_snapshot_history_limit(self, limit: int) -> None:
        """Configura quantos snapshots live ficam retidos em memoria."""
        self.snapshot_history_limit = max(1, int(limit))
        self._trim_snapshot_history()

    def get_session_summary(self) -> LiveResearchSessionSummary:
        """Calcula resumo estatistico da sessao live em memoria."""
        records = self.list_snapshot_history()
        if not records:
            return LiveResearchSessionSummary()

        confidences = [record.confidence for record in records]
        decisions = [record.decision.upper() for record in records]
        last_record = records[-1]
        return LiveResearchSessionSummary(
            total_snapshots=len(records),
            buy_count=decisions.count("BUY"),
            sell_count=decisions.count("SELL"),
            wait_count=decisions.count("WAIT"),
            average_confidence=sum(confidences) / len(confidences),
            highest_confidence=max(confidences),
            lowest_confidence=min(confidences),
            last_decision=last_record.decision,
            last_timestamp=last_record.timestamp,
        )

    def list_signal_quality(self) -> list[LiveResearchSignalQuality]:
        """Calcula qualidade dos sinais por estrategia em memoria."""
        grouped: dict[str, list[LiveResearchSignalRecord]] = {}
        for snapshot in self.list_snapshot_history():
            for signal in snapshot.signals:
                grouped.setdefault(signal.strategy_name, []).append(signal)

        rows: list[LiveResearchSignalQuality] = []
        for strategy_name in sorted(grouped):
            signals = grouped[strategy_name]
            decisions = [signal.decision.upper() for signal in signals]
            confidences = [signal.confidence for signal in signals]
            rows.append(
                LiveResearchSignalQuality(
                    strategy_name=strategy_name,
                    signal_count=len(signals),
                    buy_count=decisions.count("BUY"),
                    sell_count=decisions.count("SELL"),
                    wait_count=decisions.count("WAIT"),
                    average_confidence=sum(confidences) / len(confidences),
                    last_decision=signals[-1].decision,
                )
            )
        return rows

    def _run_registered_strategies(
        self,
        candle: Candle,
        feature_snapshot: FeatureSnapshot,
        market_snapshot: MarketSnapshot,
        timeframe: str,
    ) -> list[LiveStrategyResult]:
        market_state = self._to_market_state(candle, feature_snapshot)
        results: list[LiveStrategyResult] = []
        for strategy_name in self.strategy_factory.list_available():
            strategy = self.strategy_factory.create(strategy_name)
            strategy_signal = self._strategy_signal(
                strategy,
                strategy_name,
                market_state,
                market_snapshot,
            )
            self.event_bus.publish(STRATEGY_SIGNAL_CREATED, strategy_signal)
            self._record_event()
            self.live_experiment_runner.record_signal(
                strategy_signal=strategy_signal,
                timestamp=candle.data,
                symbol=market_snapshot.symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                regime=market_snapshot.regime,
            )
            decision_context = self.decision_pipeline.processar(
                strategy_signal,
                market_snapshot,
                self._read_only_risk_decision(),
            )
            self.event_bus.publish(DECISION_CREATED, decision_context)
            self._record_event()
            results.append(
                LiveStrategyResult(
                    strategy_name=strategy_name,
                    strategy_signal=strategy_signal,
                    decision_context=decision_context,
                )
            )
        return results

    def _strategy_signal(
        self,
        strategy: Strategy,
        strategy_name: str,
        market_state: MarketState,
        market_snapshot: MarketSnapshot,
    ) -> StrategySignal:
        try:
            if hasattr(strategy, "generate_signal"):
                signal_generator = getattr(strategy, "generate_signal")
                return signal_generator(
                    candles=self.candle_history.last_n(
                        self.candle_history.count()
                    ),
                    market_snapshot=market_snapshot,
                    current_price=market_state.preco,
                )
            return strategy.analisar(market_state)
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            return StrategySignal(
                decision="WAIT",
                score=0,
                confidence=0.0,
                reasons=[
                    f"{strategy_name} incompativel com o candle live atual",
                    str(exc),
                ],
            )

    def _to_market_snapshot(
        self,
        candle: Candle,
        feature_snapshot: FeatureSnapshot,
        symbol: str,
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
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
            time_part = candle.data.split("T", maxsplit=1)[1]
            return int(time_part.split(":", maxsplit=1)[0])
        except (IndexError, ValueError):
            return 0

    def _read_only_risk_decision(self) -> RiskDecision:
        return RiskDecision(
            allowed=False,
            reason="Live research read-only. Operacao real nao autorizada.",
            max_contracts=0,
            risk_multiplier=0.0,
        )

    def _record_event(self) -> None:
        self.event_count += 1

    def _remember_snapshot(self, data: LiveResearchData) -> None:
        strategy_results = list(data.strategy_results)
        last_result = strategy_results[-1] if strategy_results else None
        last_signal = (
            last_result.strategy_signal
            if last_result is not None
            else None
        )
        self.snapshot_history.append(
            LiveResearchSnapshotRecord(
                timestamp=datetime.now(tz=UTC).isoformat(),
                symbol=data.symbol,
                timeframe=data.timeframe,
                decision=(
                    getattr(last_signal, "decision", "N/D")
                    if last_signal is not None
                    else "N/D"
                ),
                confidence=(
                    float(getattr(last_signal, "confidence", 0.0))
                    if last_signal is not None
                    else 0.0
                ),
                strategy_signals=len(strategy_results),
                decision_contexts=len(
                    [result.decision_context for result in strategy_results]
                ),
                signals=[
                    LiveResearchSignalRecord(
                        strategy_name=result.strategy_name,
                        decision=result.strategy_signal.decision,
                        confidence=float(result.strategy_signal.confidence),
                    )
                    for result in strategy_results
                ],
            )
        )
        self._trim_snapshot_history()

    def _trim_snapshot_history(self) -> None:
        excess = len(self.snapshot_history) - self.snapshot_history_limit
        if excess > 0:
            del self.snapshot_history[:excess]
