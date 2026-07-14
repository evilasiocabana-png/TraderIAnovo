"""Servico de aplicacao para execucao controlada em conta demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Protocol

from core.decision_pipeline import DecisionPipeline
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


class DemoExecutionProvider(Protocol):
    """Porta de saida para adaptadores de execucao demo."""

    def has_open_position(self, symbol: str) -> bool:
        """Retorna se ja existe posicao aberta para o simbolo."""

    def has_open_position_for_model(self, symbol: str, operational_model: str) -> bool:
        """Retorna se ja existe posicao aberta para simbolo e modelo operacional."""

    def get_open_position(self, symbol: str) -> object | None:
        """Retorna a posicao aberta do simbolo, quando existir."""

    def get_current_price(self, symbol: str) -> float | None:
        """Retorna preco atual usado para acompanhar posicao aberta."""

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        """Retorna candles recentes para politicas de estrutura."""

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        """Retorna ATR quando o provider oferecer leitura direta."""

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> object:
        """Modifica somente o SL de uma posicao demo existente."""

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> ExecutionResult:
        """Fecha uma posicao demo existente quando a politica permitir."""

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        """Envia uma ordem ja validada para o ambiente demo."""


@dataclass(frozen=True)
class DemoExecutionPolicy:
    """Travas operacionais obrigatorias para execucao demo."""

    max_daily_operations: int = 3
    max_daily_loss: float = 500.0
    allowed_start: str = "09:00"
    allowed_end: str = "18:00"


@dataclass(frozen=True)
class DemoExecutionAuditRecord:
    """Registro imutavel de uma tentativa de execucao demo."""

    timestamp: str
    symbol: str
    side: str
    quantity: float
    accepted: bool
    status: str
    message: str
    ticket: int | None = None
    alpha_id: str = "N/D"
    alpha_version: str = "N/D"
    beta_id: str = "BETA001"
    beta_version: str = "BETA v1"
    beta_mode: str = "PROTECT_ONLY"
    operational_model: str = "MODELO_1_ALPHA_ATUAL"
    session_policy_version: str = "N/D"
    execution_pipeline_version: str = "N/D"
    lab_configuration_version: str = "N/D"
    trade_plan_version: str = "N/D"
    execution_engine_version: str = "N/D"
    indicator_bundle_version: str = "N/D"
    microstructure_version: str = "N/D"
    validation_pipeline_version: str = "N/D"
    strategy_definition_version: str = "N/D"
    technical_score: float = 0.0
    historical_confirmation: float = 0.0
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    candle_time: str = "N/D"
    mt5_position: str = "N/D"
    forex_session: str = "N/D"
    forex_session_open: bool = False
    session_filter_enabled: bool = True
    session_filter_result: str = "N/D"
    session_reason: str = "N/D"
    timestamp_utc: str = "N/D"
    timestamp_brt: str = "N/D"
    weekday: str = "N/D"
    is_rollover: bool = False
    is_london_ny_overlap: bool = False
    is_sunday_open: bool = False
    is_friday_late: bool = False


@dataclass
class DisabledDemoExecutionProvider:
    """Provider seguro usado enquanto nenhum adaptador externo foi injetado."""

    def has_open_position(self, symbol: str) -> bool:
        return False

    def has_open_position_for_model(self, symbol: str, operational_model: str) -> bool:
        return False

    def get_open_position(self, symbol: str) -> object | None:
        return None

    def get_current_price(self, symbol: str) -> float | None:
        return None

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        return []

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        return None

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            status="PROVIDER_DISABLED",
            message="Provider de execucao demo nao configurado.",
        )

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            status="PROVIDER_DISABLED",
            message="Provider de execucao demo nao configurado para fechamento.",
        )

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            status="PROVIDER_DISABLED",
            message="Provider de execucao demo nao configurado.",
        )


@dataclass
class DemoExecutionService:
    """Orquestra StrategySignal -> DecisionContext -> ordem demo validada."""

    provider: DemoExecutionProvider = field(default_factory=DisabledDemoExecutionProvider)
    decision_pipeline: DecisionPipeline = field(default_factory=DecisionPipeline)
    policy: DemoExecutionPolicy = field(default_factory=DemoExecutionPolicy)
    daily_operations: int = 0
    daily_result: float = 0.0
    audit_log: list[DemoExecutionAuditRecord] = field(default_factory=list)
    pending_audit_metadata: dict[str, object] = field(default_factory=dict)

    def prepare_order(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        risk_decision: RiskDecision,
        entry_price: float,
        stop_points: float,
        target_points: float,
    ) -> tuple[DecisionContext, ExecutionOrder | None]:
        """Cria contexto e ordem somente quando decisao e risco permitem."""
        context = self.decision_pipeline.processar(
            strategy_signal,
            market_snapshot,
            risk_decision,
        )
        if not context.approved or context.final_decision not in {"BUY", "SELL"}:
            return context, None
        order = self._build_order(
            context,
            market_snapshot,
            entry_price,
            stop_points,
            target_points,
        )
        return context, order

    def submit_demo_order(
        self,
        decision_context: DecisionContext,
        order: ExecutionOrder | None,
        paper_validated: bool,
    ) -> ExecutionResult:
        """Aplica travas e envia a ordem para o provider demo configurado."""
        rejection = self._rejection_reason(
            decision_context,
            order,
            paper_validated,
        )
        if rejection is not None:
            result = ExecutionResult(False, "REJECTED", rejection)
            self._record(order, result)
            return result

        if order is None:
            result = ExecutionResult(False, "REJECTED", "Ordem ausente.")
            self._record(order, result)
            return result

        result = self.provider.submit_order(order)
        if result.accepted:
            self.daily_operations += 1
        self._record(order, result)
        return result

    def get_open_position(self, symbol: str) -> object | None:
        """Consulta posicao aberta pelo provider demo."""
        return self.provider.get_open_position(symbol)

    def get_current_price(self, symbol: str) -> float | None:
        """Consulta preco atual pelo provider demo."""
        return self.provider.get_current_price(symbol)

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        """Consulta candles recentes pelo provider demo."""
        return self.provider.get_recent_candles(symbol, timeframe, limit)

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        """Consulta ATR pelo provider demo."""
        return self.provider.get_atr(symbol, timeframe, period)

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> object:
        """Solicita ao provider demo a alteracao apenas do SL."""
        return self.provider.modify_position_sl(symbol, ticket, new_stop)

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> ExecutionResult:
        """Solicita fechamento de posicao demo existente ao provider."""
        return self.provider.close_position(
            symbol=symbol,
            ticket=ticket,
            side=side,
            volume=volume,
            reason=reason,
        )

    def register_daily_result(self, result_points: float) -> None:
        """Atualiza perda/ganho do dia para travas posteriores."""
        self.daily_result += float(result_points)

    def list_audit_log(self) -> list[DemoExecutionAuditRecord]:
        """Retorna historico das tentativas de execucao demo."""
        return list(self.audit_log)

    def _build_order(
        self,
        context: DecisionContext,
        market_snapshot: MarketSnapshot,
        entry_price: float,
        stop_points: float,
        target_points: float,
    ) -> ExecutionOrder:
        side = context.final_decision
        return ExecutionOrder(
            symbol=market_snapshot.symbol,
            side=side,
            quantity=context.risk_decision.max_contracts,
            entry_price=float(entry_price),
            stop=self._stop(side, entry_price, stop_points),
            target=self._target(side, entry_price, target_points),
        )

    def _rejection_reason(
        self,
        context: DecisionContext,
        order: ExecutionOrder | None,
        paper_validated: bool,
    ) -> str | None:
        if not paper_validated:
            return "Paper Validation obrigatoria antes da execucao demo."
        if not context.approved:
            return f"RiskEngine rejeitou a decisao: {context.risk_decision.reason}"
        if context.final_decision not in {"BUY", "SELL"}:
            return "DecisionPipeline nao aprovou BUY/SELL operacional."
        if order is None:
            return "Ordem ausente."
        if self.daily_operations >= self.policy.max_daily_operations:
            return "Limite de operacoes por dia atingido."
        if self.daily_result <= -abs(self.policy.max_daily_loss):
            return "Limite de perda diaria atingido."
        if order.quantity <= 0:
            return "Quantidade invalida para execucao demo."
        if order.quantity > context.risk_decision.max_contracts:
            return "Quantidade acima do limite aprovado pelo RiskEngine."
        if not self._has_required_stop_and_target(order):
            return "Stop Loss e Take Profit sao obrigatorios."
        if not self._is_trade_time_allowed(context.market_snapshot.datetime):
            return "Horario fora da janela permitida para operar."
        if self._has_open_position_for_same_model(order):
            return "Ja existe uma posicao aberta para este simbolo neste modelo."
        return None

    def _has_open_position_for_same_model(self, order: ExecutionOrder) -> bool:
        operational_model = str(
            getattr(order, "operational_model", "")
            or self.pending_audit_metadata.get(
                "operational_model",
                "MODELO_1_ALPHA_ATUAL",
            )
        )
        model_checker = getattr(self.provider, "has_open_position_for_model", None)
        if callable(model_checker):
            return bool(model_checker(order.symbol, operational_model))
        return bool(self.provider.has_open_position(order.symbol))

    def _has_required_stop_and_target(self, order: ExecutionOrder) -> bool:
        if order.side == "BUY":
            return order.stop < order.entry_price < order.target
        if order.side == "SELL":
            return order.target < order.entry_price < order.stop
        return False

    def _is_trade_time_allowed(self, value: str) -> bool:
        current = self._time_from_text(value)
        return self._policy_time(self.policy.allowed_start) <= current <= self._policy_time(
            self.policy.allowed_end
        )

    def _time_from_text(self, value: str) -> time:
        text = str(value).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
        ):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                continue
        return time(0, 0)

    def _policy_time(self, value: str) -> time:
        hour, minute = str(value).split(":", maxsplit=1)
        return time(hour=int(hour), minute=int(minute))

    def _stop(self, side: str, entry_price: float, stop_points: float) -> float:
        if side == "BUY":
            return float(entry_price - stop_points)
        return float(entry_price + stop_points)

    def _target(self, side: str, entry_price: float, target_points: float) -> float:
        if side == "BUY":
            return float(entry_price + target_points)
        return float(entry_price - target_points)

    def _record(
        self,
        order: ExecutionOrder | None,
        result: ExecutionResult,
    ) -> None:
        metadata = dict(self.pending_audit_metadata)
        self.pending_audit_metadata.clear()
        self.audit_log.append(
            DemoExecutionAuditRecord(
                timestamp=datetime.now().astimezone().isoformat(),
                symbol=getattr(order, "symbol", "N/D"),
                side=getattr(order, "side", "N/D"),
                quantity=float(getattr(order, "quantity", 0) or 0),
                accepted=result.accepted,
                status=result.status,
                message=result.message,
                ticket=result.ticket,
                alpha_id=str(metadata.get("alpha_id", "N/D")),
                alpha_version=str(metadata.get("alpha_version", "N/D")),
                beta_id=str(metadata.get("beta_id", "BETA001")),
                beta_version=str(metadata.get("beta_version", "BETA v1")),
                beta_mode=str(metadata.get("beta_mode", "PROTECT_ONLY")),
                operational_model=str(
                    metadata.get("operational_model", "MODELO_1_ALPHA_ATUAL")
                ),
                session_policy_version=str(
                    metadata.get("session_policy_version", "N/D")
                ),
                execution_pipeline_version=str(
                    metadata.get("execution_pipeline_version", "N/D")
                ),
                lab_configuration_version=str(
                    metadata.get("lab_configuration_version", "N/D")
                ),
                trade_plan_version=str(metadata.get("trade_plan_version", "N/D")),
                execution_engine_version=str(
                    metadata.get("execution_engine_version", "N/D")
                ),
                indicator_bundle_version=str(
                    metadata.get("indicator_bundle_version", "N/D")
                ),
                microstructure_version=str(
                    metadata.get("microstructure_version", "N/D")
                ),
                validation_pipeline_version=str(
                    metadata.get("validation_pipeline_version", "N/D")
                ),
                strategy_definition_version=str(
                    metadata.get("strategy_definition_version", "N/D")
                ),
                technical_score=float(metadata.get("technical_score", 0.0) or 0.0),
                historical_confirmation=float(
                    metadata.get("historical_confirmation", 0.0) or 0.0
                ),
                entry_price=getattr(order, "entry_price", None),
                stop=getattr(order, "stop", None),
                target=getattr(order, "target", None),
                risk_reward=float(metadata.get("risk_reward", 0.0) or 0.0),
                candle_time=str(metadata.get("candle_time", "N/D")),
                mt5_position=str(metadata.get("mt5_position", "N/D")),
                forex_session=str(metadata.get("forex_session", "N/D")),
                forex_session_open=bool(metadata.get("forex_session_open", False)),
                session_filter_enabled=bool(
                    metadata.get("session_filter_enabled", True)
                ),
                session_filter_result=str(
                    metadata.get("session_filter_result", "N/D")
                ),
                session_reason=str(metadata.get("session_reason", "N/D")),
                timestamp_utc=str(metadata.get("timestamp_utc", "N/D")),
                timestamp_brt=str(metadata.get("timestamp_brt", "N/D")),
                weekday=str(metadata.get("weekday", "N/D")),
                is_rollover=bool(metadata.get("is_rollover", False)),
                is_london_ny_overlap=bool(
                    metadata.get("is_london_ny_overlap", False)
                ),
                is_sunday_open=bool(metadata.get("is_sunday_open", False)),
                is_friday_late=bool(metadata.get("is_friday_late", False)),
            )
        )
