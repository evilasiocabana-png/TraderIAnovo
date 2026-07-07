"""Motor de paper trading isolado do TraderIA."""

from dataclasses import dataclass, field

from core.decision_pipeline import DecisionPipeline
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from risk.risk_engine import RiskEngine


@dataclass(frozen=True)
class PaperOrder:
    """Ordem paper gerada apenas em memoria."""

    execution_order: ExecutionOrder
    status: str = "CREATED"


@dataclass
class PaperPosition:
    """Estado de uma posicao paper."""

    side: str
    quantity: int
    entry_price: float
    stop: float
    target: float
    status: str = "OPEN"
    exit_price: float | None = None
    result_points: float = 0.0
    close_reason: str | None = None


@dataclass(frozen=True)
class PaperTrade:
    """Operacao paper encerrada."""

    side: str
    quantity: int
    entry_price: float
    exit_price: float
    result_points: float
    close_reason: str


@dataclass(frozen=True)
class PaperTradingResult:
    """Resultado da ultima chamada do motor paper."""

    position: PaperPosition | None
    order: PaperOrder | None
    trade: PaperTrade | None
    decision_context: DecisionContext
    equity_curve: list[float]
    trades_history: list[PaperTrade]


@dataclass
class PaperTradingEngine:
    """Executa simulacao paper sem broker, MT5 ou ordem real."""

    stop_points: float = 50.0
    target_points: float = 100.0
    quantity: int = 1
    decision_pipeline: DecisionPipeline = field(default_factory=DecisionPipeline)
    risk_engine: RiskEngine = field(default_factory=lambda: RiskEngine(
        perda_maxima_dia=-1_000_000.0,
        limite_operacoes=1_000_000,
        score_minimo=0,
    ))
    current_position: PaperPosition | None = None
    trades_history: list[PaperTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=lambda: [0.0])

    def process(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
    ) -> PaperTradingResult:
        """Processa sinal e mercado, atualizando somente estado paper."""
        price = self._market_price(market_snapshot)
        closed_trade = self._update_position(strategy_signal, price)
        order = None
        if closed_trade is None:
            order = self._open_position_if_allowed(
                strategy_signal,
                market_snapshot,
                price,
            )
        decision_context = self._decision_context(strategy_signal, market_snapshot)
        return PaperTradingResult(
            position=self.current_position,
            order=order,
            trade=closed_trade,
            decision_context=decision_context,
            equity_curve=list(self.equity_curve),
            trades_history=list(self.trades_history),
        )

    def _update_position(
        self,
        strategy_signal: StrategySignal,
        price: float,
    ) -> PaperTrade | None:
        if self.current_position is None:
            return None
        reason = self._close_reason(self.current_position, strategy_signal, price)
        if reason is None:
            return None
        return self._close_position(price, reason)

    def _open_position_if_allowed(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        price: float,
    ) -> PaperOrder | None:
        if self.current_position is not None:
            return None
        if strategy_signal.decision not in {"BUY", "SELL"}:
            return None
        decision = self._decision_context(strategy_signal, market_snapshot)
        if not decision.approved:
            return None
        order = PaperOrder(self._execution_order(strategy_signal.decision, price))
        self.current_position = self._position_from_order(order)
        return order

    def _decision_context(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
    ) -> DecisionContext:
        risk_decision = self._risk_decision(strategy_signal)
        return self.decision_pipeline.processar(
            strategy_signal,
            market_snapshot,
            risk_decision,
        )

    def _risk_decision(self, strategy_signal: StrategySignal) -> RiskDecision:
        legacy_decision = self.risk_engine.avaliar(strategy_signal)
        return RiskDecision(
            allowed=bool(legacy_decision.aprovado),
            reason=str(legacy_decision.motivo),
            max_contracts=self.quantity,
            risk_multiplier=1.0,
        )

    def _execution_order(self, side: str, price: float) -> ExecutionOrder:
        return ExecutionOrder(
            side=side,
            quantity=self.quantity,
            entry_price=price,
            stop=self._stop_price(side, price),
            target=self._target_price(side, price),
        )

    def _position_from_order(self, order: PaperOrder) -> PaperPosition:
        execution_order = order.execution_order
        return PaperPosition(
            side=execution_order.side,
            quantity=execution_order.quantity,
            entry_price=execution_order.entry_price,
            stop=execution_order.stop,
            target=execution_order.target,
        )

    def _close_reason(
        self,
        position: PaperPosition,
        strategy_signal: StrategySignal,
        price: float,
    ) -> str | None:
        stop_or_target = self._stop_or_target_reason(position, price)
        if stop_or_target is not None:
            return stop_or_target
        if self._is_reversal(position, strategy_signal):
            return "REVERSAL"
        return None

    def _stop_or_target_reason(
        self,
        position: PaperPosition,
        price: float,
    ) -> str | None:
        if position.side == "BUY" and price <= position.stop:
            return "STOP"
        if position.side == "BUY" and price >= position.target:
            return "TARGET"
        if position.side == "SELL" and price >= position.stop:
            return "STOP"
        if position.side == "SELL" and price <= position.target:
            return "TARGET"
        return None

    def _is_reversal(
        self,
        position: PaperPosition,
        strategy_signal: StrategySignal,
    ) -> bool:
        return (
            position.side == "BUY"
            and strategy_signal.decision == "SELL"
        ) or (
            position.side == "SELL"
            and strategy_signal.decision == "BUY"
        )

    def _close_position(self, price: float, reason: str) -> PaperTrade:
        position = self.current_position
        if position is None:
            raise RuntimeError("Nenhuma posicao paper aberta.")
        position.status = reason
        position.exit_price = price
        position.result_points = self._result_points(position, price)
        position.close_reason = reason
        trade = self._trade_from_position(position)
        self.trades_history.append(trade)
        self._update_equity(trade)
        self.risk_engine.registrar_resultado(trade.result_points)
        self.current_position = None
        return trade

    def _trade_from_position(self, position: PaperPosition) -> PaperTrade:
        return PaperTrade(
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=float(position.exit_price),
            result_points=position.result_points,
            close_reason=str(position.close_reason),
        )

    def _result_points(self, position: PaperPosition, exit_price: float) -> float:
        if position.side == "BUY":
            return (exit_price - position.entry_price) * position.quantity
        return (position.entry_price - exit_price) * position.quantity

    def _update_equity(self, trade: PaperTrade) -> None:
        self.equity_curve.append(self.equity_curve[-1] + trade.result_points)

    def _stop_price(self, side: str, price: float) -> float:
        if side == "BUY":
            return price - self.stop_points
        return price + self.stop_points

    def _target_price(self, side: str, price: float) -> float:
        if side == "BUY":
            return price + self.target_points
        return price - self.target_points

    def _market_price(self, market_snapshot: MarketSnapshot) -> float:
        for name in ("price", "close", "last_price", "fechamento"):
            if hasattr(market_snapshot, name):
                return float(getattr(market_snapshot, name))
        return float(market_snapshot.market_dna_score)
