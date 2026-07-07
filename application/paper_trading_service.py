"""Servico de aplicacao para paper trading controlado da Alpha001."""

from dataclasses import dataclass, field

from core.configuration_manager import ConfigurationManager
from core.decision_pipeline import DecisionPipeline
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from risk.risk_engine import RiskDecision as EngineRiskDecision
from risk.risk_engine import RiskEngine
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy
from strategies.strategy_factory import StrategyFactory


@dataclass(frozen=True)
class PaperTradingResult:
    """Resultado de uma avaliacao paper da Alpha001."""

    strategy_signal: StrategySignal
    risk_decision: RiskDecision
    decision_context: DecisionContext
    order: ExecutionOrder | None
    real_trading_authorized: bool
    broker_integrated: bool
    mt5_integrated: bool
    message: str


@dataclass(frozen=True)
class PaperTradingReport:
    """Relatorio operacional do paper trading Alpha001."""

    total_operations: int
    paper_win_rate: float
    accumulated_result_points: float
    max_drawdown_points: float
    max_loss_sequence: int
    current_position: object | None
    status: str = "PAPER ONLY"


@dataclass
class PaperTradingService:
    """Orquestra paper trading sem corretora e sem ordem real."""

    strategy_factory: StrategyFactory = field(default_factory=StrategyFactory)
    decision_pipeline: DecisionPipeline = field(default_factory=DecisionPipeline)
    risk_engine: RiskEngine | None = None
    paper_history: list[ExecutionOrder] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.risk_engine is None:
            self.risk_engine = self._default_risk_engine()

    def alpha001_strategy(self) -> Alpha001IORBStrategy:
        """Retorna Alpha001 pela factory oficial registrada."""
        strategy = self.strategy_factory.create("alpha001_iorb")
        if not isinstance(strategy, Alpha001IORBStrategy):
            raise TypeError("Alpha001IORBStrategy nao registrada corretamente")
        return strategy

    def process_signal(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        entry_price: float,
    ) -> PaperTradingResult:
        """Processa um sinal e cria somente ordem paper quando permitido."""
        risk_decision = self._risk_contract(
            self._evaluate_risk(strategy_signal),
        )
        decision_context = self.decision_pipeline.processar(
            strategy_signal,
            market_snapshot,
            risk_decision,
        )
        order = self._build_paper_order(decision_context, entry_price)
        if order is not None:
            self.paper_history.append(order)
        return self._result(strategy_signal, risk_decision, decision_context, order)

    def list_paper_history(self) -> list[ExecutionOrder]:
        """Lista ordens paper registradas em memoria."""
        return list(self.paper_history)

    def clear_history(self) -> None:
        """Limpa historico paper em memoria."""
        self.paper_history.clear()

    def generate_report(self) -> PaperTradingReport:
        """Consolida resultados paper existentes sem executar estrategia."""
        closed_results = self._closed_results()
        return PaperTradingReport(
            total_operations=len(self.paper_history),
            paper_win_rate=self._paper_win_rate(closed_results),
            accumulated_result_points=sum(closed_results),
            max_drawdown_points=self._max_drawdown(closed_results),
            max_loss_sequence=self._max_loss_sequence(closed_results),
            current_position=self._current_position(),
        )

    def _default_risk_engine(self) -> RiskEngine:
        configuration = ConfigurationManager.get_configuration()
        return RiskEngine(
            perda_maxima_dia=configuration.max_daily_loss,
            limite_operacoes=configuration.max_daily_operations,
            score_minimo=configuration.minimum_score,
        )

    def _evaluate_risk(
        self,
        strategy_signal: StrategySignal,
    ) -> EngineRiskDecision:
        if self.risk_engine is None:
            raise RuntimeError("RiskEngine indisponivel")
        return self.risk_engine.avaliar(strategy_signal)

    def _risk_contract(
        self,
        risk: EngineRiskDecision,
    ) -> RiskDecision:
        return RiskDecision(
            allowed=risk.aprovado,
            reason=risk.motivo,
            max_contracts=self._max_contracts(risk),
            risk_multiplier=1.0 if risk.aprovado else 0.0,
        )

    def _max_contracts(self, risk: EngineRiskDecision) -> int:
        if not risk.aprovado:
            return 0
        return ConfigurationManager.get_configuration().contracts

    def _build_paper_order(
        self,
        context: DecisionContext,
        entry_price: float,
    ) -> ExecutionOrder | None:
        if not context.approved or context.final_decision not in {"BUY", "SELL"}:
            return None
        configuration = ConfigurationManager.get_configuration()
        return ExecutionOrder(
            side=context.final_decision,
            quantity=context.risk_decision.max_contracts,
            entry_price=float(entry_price),
            stop=self._stop(context.final_decision, entry_price, configuration),
            target=self._target(context.final_decision, entry_price, configuration),
        )

    def _stop(self, side: str, entry_price: float, configuration: object) -> float:
        if side == "BUY":
            return float(entry_price - configuration.stop_points)
        return float(entry_price + configuration.stop_points)

    def _target(self, side: str, entry_price: float, configuration: object) -> float:
        if side == "BUY":
            return float(entry_price + configuration.target_points)
        return float(entry_price - configuration.target_points)

    def _result(
        self,
        signal: StrategySignal,
        risk: RiskDecision,
        context: DecisionContext,
        order: ExecutionOrder | None,
    ) -> PaperTradingResult:
        return PaperTradingResult(
            strategy_signal=signal,
            risk_decision=risk,
            decision_context=context,
            order=order,
            real_trading_authorized=False,
            broker_integrated=False,
            mt5_integrated=False,
            message=self._message(order),
        )

    def _message(self, order: ExecutionOrder | None) -> str:
        if order is None:
            return "Nenhuma ordem paper criada."
        return "Ordem paper criada. Nenhuma ordem real foi enviada."

    def _closed_results(self) -> list[float]:
        return [
            float(getattr(item, "result_points"))
            for item in self.paper_history
            if hasattr(item, "result_points")
        ]

    def _paper_win_rate(self, results: list[float]) -> float:
        if not results:
            return 0.0
        wins = sum(1 for result in results if result > 0)
        return wins / len(results)

    def _max_drawdown(self, results: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for result in results:
            equity += result
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    def _max_loss_sequence(self, results: list[float]) -> int:
        current_sequence = 0
        max_sequence = 0
        for result in results:
            if result < 0:
                current_sequence += 1
                max_sequence = max(max_sequence, current_sequence)
            else:
                current_sequence = 0
        return max_sequence

    def _current_position(self) -> object | None:
        open_positions = [
            item for item in self.paper_history
            if self._is_open_position(item)
        ]
        if not open_positions:
            return None
        return open_positions[-1]

    def _is_open_position(self, item: object) -> bool:
        if isinstance(item, ExecutionOrder):
            return True
        return getattr(item, "status", "") == "OPEN"
