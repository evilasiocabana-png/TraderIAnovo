"""Position Manager para acompanhar SL de posicoes MT5 Demo abertas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from application.demo_execution_service import DisabledDemoExecutionProvider

DEFAULT_BETA_ID = "BETA001"
DEFAULT_BETA_VERSION = "BETA v1"


class PositionManagerProvider(Protocol):
    """Porta MT5 necessaria para gestao de posicao aberta."""

    def get_open_position(self, symbol: str) -> object | None:
        """Retorna a posicao aberta do simbolo, quando existir."""

    def get_current_price(self, symbol: str) -> float | None:
        """Retorna o preco atual usado para validar SL."""

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        """Retorna candles recentes para futuras politicas de estrutura."""

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        """Retorna ATR atual quando o provider suportar calculo direto."""

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> object:
        """Modifica somente o SL de uma posicao existente."""

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> object:
        """Fecha uma posicao demo existente por porta de aplicacao."""


@dataclass(frozen=True)
class PositionTradePlan:
    """Plano valido do Lab usado para gerir uma posicao ja aberta."""

    symbol: str
    side: str
    entry: float
    stop: float
    target: float | None
    stop_management: str
    stop_management_parameters: dict[str, Any] = field(default_factory=dict)
    alpha_id: str = "ALPHA001"
    alpha_version: str = "v1"
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"
    atr: float | None = None
    momentum: float | None = None
    volatility: float | None = None
    spread: float | None = None
    time_in_position_minutes: float | None = None
    support: float | None = None
    resistance: float | None = None
    swing_high: float | None = None
    swing_low: float | None = None
    timeframe: str = "M1"
    status: str = "PLANO_VALIDO"
    candle_time: str = "N/D"
    source: str = "RESEARCH_LAB"

    @classmethod
    def from_signal(cls, signal: dict[str, Any]) -> "PositionTradePlan | None":
        """Cria plano operacional a partir do JSON visual/sinal salvo."""
        symbol = str(signal.get("symbol") or signal.get("pair") or "").upper()
        side = str(
            signal.get("decision")
            or signal.get("theoretical_entry_direction")
            or ""
        ).upper()
        entry = _positive_float(signal.get("entry"))
        stop = _positive_float(signal.get("stop"))
        target = _positive_float(signal.get("target"))
        if not symbol or side not in {"BUY", "SELL"} or entry is None or stop is None:
            return None
        indicators = signal.get("market_indicators") or {}
        atr = _positive_float(indicators.get("atr"))
        if atr is None:
            atr = _positive_float(signal.get("atr"))
        momentum = _optional_float(indicators.get("momentum"))
        if momentum is None:
            momentum = _optional_float(signal.get("momentum"))
        volatility = _positive_float(indicators.get("volatility"))
        if volatility is None:
            volatility = _positive_float(signal.get("volatility"))
        spread = _non_negative_optional_float(indicators.get("spread"))
        if spread is None:
            spread = _non_negative_optional_float(signal.get("spread"))
        time_in_position_minutes = _non_negative_optional_float(
            signal.get("time_in_position_minutes")
            or signal.get("position_age_minutes")
        )
        return cls(
            symbol=symbol,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
            stop_management=str(
                signal.get("stop_management")
                or signal.get("dynamic_exit_policy")
                or "FIXED_STOP"
            ).upper(),
            stop_management_parameters=dict(
                signal.get("stop_management_parameters") or {}
            ),
            alpha_id=str(
                signal.get("alpha_id")
                or signal.get("lab_alpha_id")
                or "ALPHA001"
            ),
            alpha_version=str(signal.get("alpha_version") or "v1"),
            beta_id=_normalize_beta_id(signal.get("beta_id")),
            beta_version=str(signal.get("beta_version") or DEFAULT_BETA_VERSION),
            beta_mode=str(signal.get("beta_mode") or "PROTECT_ONLY").upper(),
            atr=atr,
            momentum=momentum,
            volatility=volatility,
            spread=spread,
            time_in_position_minutes=time_in_position_minutes,
            support=_positive_float(indicators.get("support") or signal.get("support")),
            resistance=_positive_float(
                indicators.get("resistance") or signal.get("resistance")
            ),
            swing_high=_positive_float(
                indicators.get("swing_high") or signal.get("swing_high")
            ),
            swing_low=_positive_float(
                indicators.get("swing_low") or signal.get("swing_low")
            ),
            timeframe=str(signal.get("timeframe") or "M1"),
            status=str(signal.get("plan_status") or "PLANO_VALIDO").upper(),
            candle_time=str(signal.get("last_candle_time") or "N/D"),
            source=str(signal.get("lab_configuration_source") or "RESEARCH_LAB"),
        )


@dataclass(frozen=True)
class PositionStateSnapshot:
    """Leitura leve da posicao e do mercado usada na decisao."""

    symbol: str
    ticket: int
    side: str
    volume: float
    entry_price: float
    current_price: float
    current_stop: float
    current_target: float | None
    r_multiple: float
    distance_to_target_r: float | None
    time_in_position_minutes: float | None
    atr: float | None
    momentum: float | None
    volatility: float | None
    spread: float | None
    state: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class PositionManagerDecision:
    """Decisao auditavel antes da execucao."""

    symbol: str
    ticket: int
    state: str
    action: str
    reason: str
    confidence: float
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"
    allowed_to_execute: bool = False
    execution_mode: str = "READ_ONLY"
    requested_stop: float | None = None
    requested_close_volume: float | None = None
    final_exit_reason: str = "N/D"
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class PositionManagerResult:
    """Resultado auditavel de um ciclo de gestao de SL."""

    symbol: str
    status: str
    action: str
    message: str
    ticket: int | None = None
    policy: str = "N/D"
    execution_mode: str = "READ_ONLY"
    execution_status: str = "BLOCKED"
    side: str = "N/D"
    old_stop: float | None = None
    new_stop: float | None = None
    current_price: float | None = None
    entry: float | None = None
    atr: float | None = None
    r_multiple: float = 0.0
    position_state: str = "N/D"
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()
    final_exit_reason: str = "N/D"
    requested_close_volume: float | None = None
    candle_time: str = "N/D"
    missing_data: tuple[str, ...] = ()
    audit_tags: tuple[str, ...] = ()
    provider_result: str = "N/D"
    submitted: bool = False
    success: bool = False
    alpha_id: str = "ALPHA001"
    alpha_version: str = "v1"
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"


@dataclass
class PositionManagerService:
    """Acompanha posicoes abertas sem abrir novas entradas."""

    provider: PositionManagerProvider = field(
        default_factory=DisabledDemoExecutionProvider
    )
    assisted_execution_enabled: bool = False
    early_exit_enabled: bool = False
    log_path: Path = field(
        default_factory=lambda: Path(".traderia") / "position_manager.jsonl"
    )

    def manage_signals(
        self,
        signals: list[dict[str, Any]],
    ) -> list[PositionManagerResult]:
        """Executa gestao para todos os planos validos salvos."""
        plans: list[PositionTradePlan] = []
        invalid_symbols: set[str] = set()
        for signal in signals:
            symbol = str(signal.get("symbol") or signal.get("pair") or "").upper()
            plan = PositionTradePlan.from_signal(signal)
            if plan is None:
                if symbol:
                    invalid_symbols.add(symbol)
                continue
            plans.append(plan)
        results = [self.manage_plan(plan) for plan in plans]
        for symbol in sorted(invalid_symbols - {plan.symbol for plan in plans}):
            results.append(
                self._record(
                    PositionManagerResult(
                        symbol=symbol,
                        status="TRADE_PLAN_ABSENT",
                        action="STOP_MAINTAINED",
                        message="Plano valido ausente ou incompleto; SL preservado.",
                        missing_data=("trade_plan",),
                        audit_tags=("TRADE_PLAN_ABSENT",),
                    )
                )
            )
        return results

    def manage_plan(self, plan: PositionTradePlan) -> PositionManagerResult:
        """Avalia uma posicao aberta contra o plano do Lab."""
        if plan.status != "PLANO_VALIDO":
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    status="TRADE_PLAN_ABSENT",
                    action="STOP_MAINTAINED",
                    message="Plano do Lab nao esta valido; SL preservado.",
                    policy=plan.stop_management,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=plan.beta_id,
                    beta_version=plan.beta_version,
                    beta_mode=plan.beta_mode,
                    side=plan.side,
                    candle_time=plan.candle_time,
                    entry=plan.entry,
                    missing_data=("trade_plan",),
                    audit_tags=("TRADE_PLAN_ABSENT",),
                )
            )

        position = self.provider.get_open_position(plan.symbol)
        if position is None:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    status="POSITION_ABSENT",
                    action="STOP_MAINTAINED",
                    message="Sem posicao aberta no MT5; nada a gerenciar.",
                    policy=plan.stop_management,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=plan.beta_id,
                    beta_version=plan.beta_version,
                    beta_mode=plan.beta_mode,
                    side=plan.side,
                    candle_time=plan.candle_time,
                    entry=plan.entry,
                    missing_data=("position",),
                    audit_tags=("POSITION_ABSENT",),
                )
            )

        side = self._position_side(position, plan.side)
        ticket = int(getattr(position, "ticket", 0) or 0)
        entry = _positive_float(getattr(position, "price_open", None)) or plan.entry
        current_stop = _positive_float(getattr(position, "sl", None))
        if current_stop is None:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="MARKET_DATA_ABSENT",
                    action="STOP_MAINTAINED",
                    message="Stop atual ausente na posicao MT5; SL preservado.",
                    policy=plan.stop_management,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=plan.beta_id,
                    beta_version=plan.beta_version,
                    beta_mode=plan.beta_mode,
                    side=side,
                    candle_time=plan.candle_time,
                    entry=entry,
                    missing_data=("current_stop",),
                    audit_tags=("MARKET_DATA_ABSENT",),
                )
            )
        current_price = self.provider.get_current_price(plan.symbol)
        if current_price is None:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="MARKET_DATA_ABSENT",
                    action="STOP_MAINTAINED",
                    message="Preco atual ausente; SL preservado.",
                    policy=plan.stop_management,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=plan.beta_id,
                    beta_version=plan.beta_version,
                    beta_mode=plan.beta_mode,
                    side=side,
                    old_stop=current_stop,
                    candle_time=plan.candle_time,
                    entry=entry,
                    missing_data=("current_price",),
                    audit_tags=("MARKET_DATA_ABSENT",),
                )
            )

        snapshot = self._position_snapshot(
            plan=plan,
            position=position,
            side=side,
            ticket=ticket,
            entry=entry,
            current_stop=current_stop,
            current_price=float(current_price),
        )
        decision = self._decide(plan, snapshot)
        if decision.action in {"EARLY_EXIT", "FULL_EXIT"}:
            return self._execute_close_decision(plan, snapshot, decision)
        if decision.action == "HOLD_POSITION":
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="POSITION_HELD",
                    action="HOLD_POSITION",
                    message=decision.reason,
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    current_price=float(current_price),
                    entry=entry,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    candle_time=plan.candle_time,
                    audit_tags=("HOLD_POSITION", decision.state),
                )
            )

        candidate = decision.requested_stop
        if candidate is None:
            status, message, missing = self._blocked_candidate_reason(plan)
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status=status,
                    action="STOP_MAINTAINED",
                    message=message,
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    current_price=float(current_price),
                    entry=entry,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    candle_time=plan.candle_time,
                    missing_data=missing,
                    audit_tags=(status,),
                )
            )
        if not self._is_better_stop(side, candidate, current_stop):
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="STOP_MOVE_BLOCKED_NOT_PROTECTIVE",
                    action="STOP_MAINTAINED",
                    message="Stop candidato nao melhora o risco; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=candidate,
                    current_price=float(current_price),
                    entry=entry,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    candle_time=plan.candle_time,
                    audit_tags=("STOP_MOVE_BLOCKED_NOT_PROTECTIVE",),
                )
            )
        if not self._is_stop_before_market(side, candidate, float(current_price)):
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="STOP_MOVE_BLOCKED_NOT_PROTECTIVE",
                    action="STOP_MAINTAINED",
                    message="Stop candidato cruza ou encosta no preco atual; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=candidate,
                    current_price=float(current_price),
                    entry=entry,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    candle_time=plan.candle_time,
                    audit_tags=("STOP_MOVE_BLOCKED_INVALID_MARKET_SIDE",),
                )
            )
        if not self.assisted_execution_enabled:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="EXECUTION_DISABLED",
                    action="STOP_MAINTAINED",
                    message=(
                        "Novo SL calculado, mas execucao assistida demo esta "
                        "desligada; SL preservado."
                    ),
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=candidate,
                    current_price=float(current_price),
                    entry=entry,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    candle_time=plan.candle_time,
                    execution_status="BLOCKED_BY_CONFIG",
                    audit_tags=("STOP_MOVE_CANDIDATE", "STOP_MOVE_BLOCKED_BY_CONFIG"),
                )
            )

        response = self.provider.modify_position_sl(plan.symbol, ticket, candidate)
        success = bool(getattr(response, "success", False) or getattr(response, "accepted", False))
        provider_message = str(getattr(response, "message", "") or "SL enviado ao MT5.")
        return self._record(
            PositionManagerResult(
                symbol=plan.symbol,
                ticket=ticket,
                status="STOP_MOVED" if success else "MODIFY_REJECTED",
                action="STOP_MOVED" if success else "STOP_MAINTAINED",
                message=provider_message,
                policy=plan.stop_management,
                side=side,
                old_stop=current_stop,
                new_stop=candidate,
                current_price=float(current_price),
                entry=entry,
                atr=plan.atr,
                r_multiple=snapshot.r_multiple,
                position_state=decision.state,
                confidence=decision.confidence,
                alpha_id=plan.alpha_id,
                alpha_version=plan.alpha_version,
                beta_id=decision.beta_id,
                beta_version=decision.beta_version,
                beta_mode=decision.beta_mode,
                evidence=decision.evidence,
                candle_time=plan.candle_time,
                execution_mode="AUTOMATIC_DEMO",
                execution_status="EXECUTED" if success else "BLOCKED",
                audit_tags=("STOP_MOVED" if success else "STOP_MOVE_FAILED",),
                provider_result=provider_message,
                submitted=True,
                success=success,
            )
        )

    def _position_snapshot(
        self,
        *,
        plan: PositionTradePlan,
        position: object,
        side: str,
        ticket: int,
        entry: float,
        current_stop: float,
        current_price: float,
    ) -> PositionStateSnapshot:
        risk = max(abs(float(entry) - float(current_stop)), 1e-12)
        favorable = current_price - entry if side == "BUY" else entry - current_price
        r_multiple = favorable / risk
        target = _positive_float(getattr(position, "tp", None)) or plan.target
        distance_to_target_r: float | None = None
        if target is not None:
            remaining = target - current_price if side == "BUY" else current_price - target
            distance_to_target_r = remaining / risk
        evidence = self._state_evidence(
            side=side,
            r_multiple=r_multiple,
            distance_to_target_r=distance_to_target_r,
            plan=plan,
        )
        return PositionStateSnapshot(
            symbol=plan.symbol,
            ticket=ticket,
            side=side,
            volume=float(getattr(position, "volume", 0.0) or 0.0),
            entry_price=entry,
            current_price=current_price,
            current_stop=current_stop,
            current_target=target,
            r_multiple=r_multiple,
            distance_to_target_r=distance_to_target_r,
            time_in_position_minutes=plan.time_in_position_minutes,
            atr=plan.atr,
            momentum=plan.momentum,
            volatility=plan.volatility,
            spread=plan.spread,
            state=self._position_state(
                side=side,
                entry=entry,
                current_stop=current_stop,
                r_multiple=r_multiple,
                evidence=evidence,
            ),
            evidence=evidence,
        )

    def _decide(
        self,
        plan: PositionTradePlan,
        snapshot: PositionStateSnapshot,
    ) -> PositionManagerDecision:
        policy = self._runtime_policy(plan)
        if snapshot.state == "BAD_EXECUTION_CONTEXT":
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="NO_ACTION_BAD_CONTEXT",
                reason="Contexto de execucao incompleto ou inseguro; posicao preservada.",
                confidence=0.0,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence,
            )
        if self.early_exit_enabled and self._early_exit_confirmed(snapshot):
            reason = self._early_exit_reason(snapshot)
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state="EXIT_REQUIRED",
                action="FULL_EXIT",
                reason=f"Saida antecipada confirmada dinamicamente: {reason}.",
                confidence=min(0.95, 0.45 + len(snapshot.evidence) * 0.12),
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                allowed_to_execute=self.assisted_execution_enabled,
                execution_mode="AUTOMATIC_DEMO"
                if self.assisted_execution_enabled
                else "READ_ONLY",
                requested_close_volume=snapshot.volume,
                final_exit_reason=reason,
                evidence=snapshot.evidence,
            )
        if snapshot.state == "NEW_POSITION":
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason="Posicao nova; preservar stop inicial e alvo original.",
                confidence=0.50,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence,
            )
        if snapshot.r_multiple < 0.50:
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason=(
                    "Trade ainda nao andou 0.50R a favor; preservar stop inicial "
                    "e dar espaco ao plano do Lab."
                ),
                confidence=0.55,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence + ("PROTECTION_WAIT_UNDER_0_50R",),
            )
        if snapshot.r_multiple < 1.00:
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason=(
                    "Trade entre 0.50R e 1.00R; Position Manager monitora, mas "
                    "nao move SL antes de confirmacao minima de 1.00R."
                ),
                confidence=0.55,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence + ("PROTECTION_WAIT_UNDER_1_00R",),
            )
        candidate = self._dynamic_candidate_stop(
            side=snapshot.side,
            entry=snapshot.entry_price,
            current_stop=snapshot.current_stop,
            current_price=snapshot.current_price,
            plan=plan,
            snapshot=snapshot,
        )
        if candidate is not None:
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="PROTECT_POSITION",
                reason="Protecao candidata definida dinamicamente pelo cenario atual.",
                confidence=0.60,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                allowed_to_execute=self.assisted_execution_enabled,
                execution_mode="AUTOMATIC_DEMO"
                if self.assisted_execution_enabled
                else "READ_ONLY",
                requested_stop=candidate,
                evidence=snapshot.evidence,
            )
        if policy == "FIXED_STOP":
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason="Politica fixa; manter plano original.",
                confidence=0.50,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence,
            )
        return PositionManagerDecision(
            symbol=plan.symbol,
            ticket=snapshot.ticket,
            state=snapshot.state,
            action="HOLD_POSITION",
            reason="Cenario sem confirmacao para protecao ou saida; manter plano original.",
            confidence=0.40,
            beta_id=plan.beta_id,
            beta_version=plan.beta_version,
            beta_mode=plan.beta_mode,
            evidence=snapshot.evidence,
        )

    def _runtime_policy(self, plan: PositionTradePlan) -> str:
        """Mantem compatibilidade com campo legado sem predefinir a saida."""
        raw_policy = str(plan.stop_management or "DYNAMIC_POSITION_MANAGER").upper()
        if raw_policy in {"", "N/D", "FIXED_STOP"}:
            return "DYNAMIC_POSITION_MANAGER"
        return raw_policy

    def _dynamic_candidate_stop(
        self,
        *,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        plan: PositionTradePlan,
        snapshot: PositionStateSnapshot,
    ) -> float | None:
        """Escolhe protecao por cenario, sem exigir saida predefinida no plano."""
        if snapshot.r_multiple < 1.00:
            return None
        candidate_sources: list[float | None]
        if snapshot.state == "MOMENTUM_WEAKNESS":
            candidate_sources = [
                self._momentum_weakness_stop(side, entry, current_price, plan),
                self._break_even_stop(side, entry, current_stop, current_price, plan),
            ]
        elif snapshot.state in {"TREND_RUNNER", "PROTECTED_POSITION"}:
            candidate_sources = [
                self._break_even_stop(side, entry, current_stop, current_price, plan),
                self._structure_based_stop(side, current_price, plan),
                self._volatility_stop(side, entry, current_price, plan),
                self._activated_atr_trailing_stop(
                    side,
                    entry,
                    current_stop,
                    current_price,
                    plan,
                    snapshot.r_multiple,
                ),
            ]
        else:
            candidate_sources = [
                self._break_even_stop(side, entry, current_stop, current_price, plan),
                self._structure_based_stop(side, current_price, plan),
            ]
        candidates: list[float] = []
        for candidate in candidate_sources:
            if candidate is None:
                continue
            if not self._is_better_stop(side, candidate, current_stop):
                continue
            if not self._is_stop_before_market(side, candidate, current_price):
                continue
            candidates.append(float(candidate))
        if not candidates:
            return None
        return max(candidates) if side == "BUY" else min(candidates)

    def _activated_atr_trailing_stop(
        self,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        plan: PositionTradePlan,
        r_multiple: float,
    ) -> float | None:
        activation_rr = _positive_float(
            plan.stop_management_parameters.get("atr_trailing_activation_rr")
        ) or 1.0
        if r_multiple < activation_rr:
            return None
        if not self._position_is_positive(side, entry, current_price):
            return None
        return self._atr_trailing_stop(side, current_price, plan)

    def _execute_close_decision(
        self,
        plan: PositionTradePlan,
        snapshot: PositionStateSnapshot,
        decision: PositionManagerDecision,
    ) -> PositionManagerResult:
        if not self.assisted_execution_enabled:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=snapshot.ticket,
                    status="EXECUTION_DISABLED",
                    action="EARLY_EXIT",
                    message=(
                        "Fechamento antecipado calculado, mas execucao demo esta "
                        "desligada; posicao preservada."
                    ),
                    policy=plan.stop_management,
                    execution_status="BLOCKED_BY_CONFIG",
                    side=snapshot.side,
                    old_stop=snapshot.current_stop,
                    current_price=snapshot.current_price,
                    entry=snapshot.entry_price,
                    atr=plan.atr,
                    r_multiple=snapshot.r_multiple,
                    position_state=decision.state,
                    confidence=decision.confidence,
                    alpha_id=plan.alpha_id,
                    alpha_version=plan.alpha_version,
                    beta_id=decision.beta_id,
                    beta_version=decision.beta_version,
                    beta_mode=decision.beta_mode,
                    evidence=decision.evidence,
                    final_exit_reason=decision.final_exit_reason,
                    requested_close_volume=decision.requested_close_volume,
                    candle_time=plan.candle_time,
                    audit_tags=("EARLY_EXIT_CANDIDATE", "BLOCKED_BY_CONFIG"),
                )
            )
        response = self.provider.close_position(
            symbol=plan.symbol,
            ticket=snapshot.ticket,
            side=snapshot.side,
            volume=float(decision.requested_close_volume or snapshot.volume),
            reason=decision.final_exit_reason,
        )
        success = bool(getattr(response, "accepted", False) or getattr(response, "success", False))
        message = str(getattr(response, "message", "") or "Fechamento enviado ao MT5 Demo.")
        return self._record(
            PositionManagerResult(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                status="POSITION_CLOSED" if success else "CLOSE_REJECTED",
                action="FULL_EXIT" if success else "EARLY_EXIT",
                message=message,
                policy=plan.stop_management,
                execution_mode="AUTOMATIC_DEMO",
                execution_status="EXECUTED" if success else "BLOCKED",
                side=snapshot.side,
                old_stop=snapshot.current_stop,
                current_price=snapshot.current_price,
                entry=snapshot.entry_price,
                atr=plan.atr,
                r_multiple=snapshot.r_multiple,
                position_state=decision.state,
                confidence=decision.confidence,
                alpha_id=plan.alpha_id,
                alpha_version=plan.alpha_version,
                beta_id=decision.beta_id,
                beta_version=decision.beta_version,
                beta_mode=decision.beta_mode,
                evidence=decision.evidence,
                final_exit_reason=decision.final_exit_reason,
                requested_close_volume=decision.requested_close_volume,
                candle_time=plan.candle_time,
                audit_tags=("FULL_EXIT_EXECUTED" if success else "FULL_EXIT_REJECTED",),
                provider_result=message,
                submitted=True,
                success=success,
            )
        )

    def _candidate_stop(
        self,
        *,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        policy = plan.stop_management
        if policy == "BREAK_EVEN":
            return self._break_even_stop(side, entry, current_stop, current_price, plan)
        if policy == "ATR_TRAILING_STOP":
            return self._atr_trailing_stop(side, current_price, plan)
        if policy == "MARKET_AWARE_STOP_PROTECTION":
            return self._market_aware_stop(side, entry, current_stop, current_price, plan)
        if policy == "VOLATILITY_STOP_PROTECTION":
            return self._volatility_stop(side, entry, current_price, plan)
        if policy == "MOMENTUM_WEAKNESS_STOP_TIGHTENING":
            return self._momentum_weakness_stop(side, entry, current_price, plan)
        if policy == "STRUCTURE_BASED_STOP_PROTECTION":
            return self._structure_based_stop(side, current_price, plan)
        return None

    def _break_even_stop(
        self,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        trigger_rr = _positive_float(
            plan.stop_management_parameters.get("break_even_trigger_rr")
        ) or 1.0
        offset_pips = _non_negative_float(
            plan.stop_management_parameters.get("break_even_offset_pips")
        )
        initial_risk = abs(float(entry) - float(current_stop))
        if initial_risk <= 0.0:
            return None
        favorable_move = current_price - entry if side == "BUY" else entry - current_price
        if favorable_move < initial_risk * trigger_rr:
            return None
        offset = offset_pips * self._pip_size(plan.symbol)
        return entry + offset if side == "BUY" else entry - offset

    def _atr_trailing_stop(
        self,
        side: str,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        if plan.atr is None:
            return None
        factor = _positive_float(
            plan.stop_management_parameters.get("atr_trailing_factor")
        ) or 2.0
        if side == "BUY":
            return current_price - float(plan.atr) * factor
        return current_price + float(plan.atr) * factor

    def _market_aware_stop(
        self,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        if not self._position_is_positive(side, entry, current_price):
            return None
        structure = self._structure_based_stop(side, current_price, plan)
        if structure is not None:
            return structure
        if self._momentum_against(side, plan):
            return entry
        if plan.atr is not None:
            return self._atr_trailing_stop(side, current_price, plan)
        return None

    def _volatility_stop(
        self,
        side: str,
        entry: float,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        if plan.atr is None or plan.volatility is None:
            return None
        if not self._position_is_positive(side, entry, current_price):
            return None
        factor = _positive_float(
            plan.stop_management_parameters.get("volatility_stop_factor")
        ) or 1.5
        if side == "BUY":
            return current_price - float(plan.atr) * factor
        return current_price + float(plan.atr) * factor

    def _momentum_weakness_stop(
        self,
        side: str,
        entry: float,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        if plan.momentum is None:
            return None
        if not self._position_is_positive(side, entry, current_price):
            return None
        if not self._momentum_against(side, plan):
            return None
        return entry

    def _structure_based_stop(
        self,
        side: str,
        current_price: float,
        plan: PositionTradePlan,
    ) -> float | None:
        pip = self._pip_size(plan.symbol)
        if side == "BUY":
            base = plan.swing_low or plan.support
            if base is None or base >= current_price:
                return None
            return float(base) - pip
        base = plan.swing_high or plan.resistance
        if base is None or base <= current_price:
            return None
        return float(base) + pip

    def _blocked_candidate_reason(
        self,
        plan: PositionTradePlan,
    ) -> tuple[str, str, tuple[str, ...]]:
        runtime_policy = self._runtime_policy(plan)
        if runtime_policy == "ATR_TRAILING_STOP" and plan.atr is None:
            return "ATR_ABSENT", "ATR ausente para trailing; SL preservado.", ("atr",)
        if (
            runtime_policy == "VOLATILITY_STOP_PROTECTION"
            and (plan.atr is None or plan.volatility is None)
        ):
            missing = tuple(
                name
                for name, value in (("atr", plan.atr), ("volatility", plan.volatility))
                if value is None
            )
            return "MARKET_DATA_ABSENT", "Dados de volatilidade ausentes; SL preservado.", missing
        if (
            runtime_policy == "MOMENTUM_WEAKNESS_STOP_TIGHTENING"
            and plan.momentum is None
        ):
            return "MARKET_DATA_ABSENT", "Momentum ausente; SL preservado.", ("momentum",)
        if runtime_policy == "STRUCTURE_BASED_STOP_PROTECTION" and not any(
            value is not None
            for value in (plan.support, plan.resistance, plan.swing_high, plan.swing_low)
        ):
            return "STRUCTURE_ABSENT", "Estrutura ausente; SL preservado.", ("structure",)
        if runtime_policy not in {
            "DYNAMIC_POSITION_MANAGER",
            "BREAK_EVEN",
            "ATR_TRAILING_STOP",
            "MARKET_AWARE_STOP_PROTECTION",
            "VOLATILITY_STOP_PROTECTION",
            "MOMENTUM_WEAKNESS_STOP_TIGHTENING",
            "STRUCTURE_BASED_STOP_PROTECTION",
            "EARLY_EXIT",
            "FULL_EXIT",
        }:
            return (
                "POLICY_BLOCKED_UNSUPPORTED_ACTION",
                "Politica sem acao MOVE_STOP segura suportada; SL preservado.",
                ("supported_policy",),
            )
        return "STOP_MAINTAINED", "Condicao segura nao atingida; SL preservado.", ()

    def _state_evidence(
        self,
        *,
        side: str,
        r_multiple: float,
        distance_to_target_r: float | None,
        plan: PositionTradePlan,
    ) -> tuple[str, ...]:
        evidence: list[str] = []
        if plan.momentum is not None and self._momentum_against(side, plan):
            evidence.append("MOMENTUM_AGAINST")
        if plan.time_in_position_minutes is not None and plan.time_in_position_minutes >= 240:
            evidence.append("TIME_DECAY")
        if r_multiple < -0.25:
            evidence.append("NEGATIVE_R")
        context_deteriorated = (
            (plan.momentum is not None and self._momentum_against(side, plan))
            or (
                plan.time_in_position_minutes is not None
                and plan.time_in_position_minutes >= 120
            )
        )
        if (
            context_deteriorated
            and r_multiple > 0.15
            and distance_to_target_r is not None
            and distance_to_target_r > 2.0
        ):
            evidence.append("LOW_PROBABILITY_TO_TARGET")
        if plan.spread is not None:
            initial_risk = abs(float(plan.entry) - float(plan.stop))
            if initial_risk > 0.0 and float(plan.spread) > initial_risk * 0.35:
                evidence.append("SPREAD_RISK")
        if (
            plan.volatility is not None
            and plan.atr is not None
            and float(plan.volatility) > float(plan.atr) * 2.5
        ):
            evidence.append("VOLATILITY_RISK")
        structure_against = (
            side == "BUY"
            and plan.support is not None
            and plan.support < plan.stop
        ) or (
            side == "SELL"
            and plan.resistance is not None
            and plan.resistance > plan.stop
        )
        if structure_against:
            evidence.append("STRUCTURE_BREAK_RISK")
        return tuple(evidence)

    def _position_state(
        self,
        *,
        side: str,
        entry: float,
        current_stop: float,
        r_multiple: float,
        evidence: tuple[str, ...],
    ) -> str:
        if "SPREAD_RISK" in evidence:
            return "BAD_EXECUTION_CONTEXT"
        if "STRUCTURE_BREAK_RISK" in evidence:
            return "STRUCTURE_BREAK_RISK"
        if "VOLATILITY_RISK" in evidence:
            return "VOLATILITY_RISK"
        if "LOW_PROBABILITY_TO_TARGET" in evidence:
            return "LOW_PROBABILITY_TO_TARGET"
        if "MOMENTUM_AGAINST" in evidence and r_multiple > 0.0:
            return "MOMENTUM_WEAKNESS"
        if "TIME_DECAY" in evidence:
            return "TIME_DECAY"
        protected = current_stop >= entry if side == "BUY" else current_stop <= entry
        if protected:
            return "PROTECTED_POSITION"
        if r_multiple >= 1.0:
            return "TREND_RUNNER"
        if r_multiple > 0.0:
            return "HEALTHY_POSITION"
        return "NEW_POSITION"

    def _early_exit_confirmed(self, snapshot: PositionStateSnapshot) -> bool:
        critical = {
            "MOMENTUM_AGAINST",
            "TIME_DECAY",
            "LOW_PROBABILITY_TO_TARGET",
            "VOLATILITY_RISK",
            "STRUCTURE_BREAK_RISK",
            "NEGATIVE_R",
        }
        hits = [item for item in snapshot.evidence if item in critical]
        return len(hits) >= 2

    def _early_exit_reason(self, snapshot: PositionStateSnapshot) -> str:
        evidence = set(snapshot.evidence)
        if "MOMENTUM_AGAINST" in evidence and "LOW_PROBABILITY_TO_TARGET" in evidence:
            return "EARLY_EXIT_MOMENTUM_LOSS"
        if "STRUCTURE_BREAK_RISK" in evidence:
            return "EARLY_EXIT_STRUCTURE_BREAK"
        if "TIME_DECAY" in evidence:
            return "EARLY_EXIT_TIME_DECAY"
        if "VOLATILITY_RISK" in evidence:
            return "EARLY_EXIT_VOLATILITY_RISK"
        if "LOW_PROBABILITY_TO_TARGET" in evidence:
            return "EARLY_EXIT_LOW_PROBABILITY"
        return "EARLY_EXIT_REVERSAL"

    def _protect_action(self, policy: str) -> str:
        if policy == "BREAK_EVEN":
            return "MOVE_TO_BREAK_EVEN"
        if policy == "ATR_TRAILING_STOP":
            return "ATR_TRAILING"
        if policy == "STRUCTURE_BASED_STOP_PROTECTION":
            return "STRUCTURE_PROTECTION"
        if policy == "VOLATILITY_STOP_PROTECTION":
            return "VOLATILITY_PROTECTION"
        if policy == "MOMENTUM_WEAKNESS_STOP_TIGHTENING":
            return "MOMENTUM_PROTECTION"
        return "PROTECT_POSITION"

    def _position_is_positive(
        self,
        side: str,
        entry: float,
        current_price: float,
    ) -> bool:
        if side == "BUY":
            return current_price > entry
        return current_price < entry

    def _momentum_against(self, side: str, plan: PositionTradePlan) -> bool:
        if plan.momentum is None:
            return False
        if side == "BUY":
            return float(plan.momentum) < 0.0
        return float(plan.momentum) > 0.0

    def _record(self, result: PositionManagerResult) -> PositionManagerResult:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "type": "POSITION_MANAGER",
            **result.__dict__,
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return result

    def _position_side(self, position: object, fallback: str) -> str:
        position_type = getattr(position, "type", None)
        if position_type == 0:
            return "BUY"
        if position_type == 1:
            return "SELL"
        side = str(getattr(position, "side", "") or fallback).upper()
        return "SELL" if side == "SELL" else "BUY"

    def _is_better_stop(self, side: str, candidate: float, current: float) -> bool:
        epsilon = 1e-10
        if side == "BUY":
            return candidate > current + epsilon
        return candidate < current - epsilon

    def _is_stop_before_market(
        self,
        side: str,
        candidate: float,
        current_price: float,
    ) -> bool:
        if side == "BUY":
            return candidate < current_price
        return candidate > current_price

    def _pip_size(self, symbol: str) -> float:
        return 0.01 if str(symbol).upper().endswith("JPY") else 0.0001


def _positive_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0.0:
        return None
    return parsed


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _non_negative_optional_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0.0 else None


def _non_negative_float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(parsed, 0.0)


def _normalize_beta_id(value: object) -> str:
    normalized = str(value or DEFAULT_BETA_ID).strip().upper()
    if normalized == "LEGACY_CURRENT_EXIT":
        return DEFAULT_BETA_ID
    return normalized or DEFAULT_BETA_ID
