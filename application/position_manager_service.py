"""Position Manager para acompanhar SL de posicoes MT5 Demo abertas."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from application.beta_strategies import BETA002_ID, Beta002Strategy
from application.demo_execution_service import DisabledDemoExecutionProvider
from domain.contracts.beta_strategy import BetaDecision, BetaStrategyContext

DEFAULT_BETA_ID = "BETA001"
DEFAULT_BETA_VERSION = "BETA v1"
DEFAULT_POSITION_MANAGER_LOG_MAX_MB = 25


class PositionManagerProvider(Protocol):
    """Porta MT5 necessaria para gestao de posicao aberta."""

    def get_open_position(self, symbol: str) -> object | None:
        """Retorna a posicao aberta do simbolo, quando existir."""

    def get_open_position_by_ticket(self, symbol: str, ticket: int) -> object | None:
        """Retorna a posicao aberta exata pelo ticket, quando existir."""

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
    ticket: int | None = None
    risk_reward: float | None = None
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
        robot_status = str(signal.get("robot_status") or "").upper()
        is_positioned = bool(signal.get("is_positioned")) or robot_status == "POSICAO_ABERTA_MT5"
        plan_status = str(signal.get("plan_status") or "PLANO_VALIDO").upper()
        if is_positioned and plan_status != "PLANO_VALIDO":
            plan_status = "PLANO_VALIDO"
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
        risk_reward = _positive_float(
            signal.get("risk_reward")
            or signal.get("research_plan_risk_reward")
            or signal.get("rr")
            or signal.get("risk_reward_ratio")
        )
        if risk_reward is None:
            risk_reward = _risk_reward_from_prices(entry, stop, target)
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
            ticket=_optional_int(
                signal.get("ticket")
                or signal.get("mt5_ticket")
                or signal.get("local_ticket")
            ),
            risk_reward=risk_reward,
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
            status=plan_status,
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
    strength_score: float = 0.0
    confirmation_count: int = 0
    state_duration: int = 0
    ema14_value: float | None = None
    ema14_slope: float | None = None
    momentum_14: float | None = None
    atr_14: float | None = None
    atr_relative_change: float | None = None
    structure_signal: str = "N/D"
    evaluated_at: str = "N/D"
    beta_closed_candle_time: str = "N/D"
    missing_data: tuple[str, ...] = ()


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
    beta_strength_score: float = 0.0
    beta_confirmation_count: int = 0
    beta_state_duration: int = 0
    beta_ema14_value: float | None = None
    beta_ema14_slope: float | None = None
    beta_momentum_14: float | None = None
    beta_atr_14: float | None = None
    beta_atr_relative_change: float | None = None
    beta_structure_signal: str = "N/D"
    beta_evaluated_at: str = "N/D"
    beta_closed_candle_time: str = "N/D"


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
    state_path: Path = field(
        default_factory=lambda: Path(".traderia") / "position_manager_state.json"
    )
    current_state_path: Path = field(
        default_factory=lambda: Path(".traderia") / "position_manager_current.json"
    )
    history_dedupe_path: Path = field(
        default_factory=lambda: Path(".traderia")
        / "position_manager_history_dedupe.json"
    )
    beta002_strategy: Beta002Strategy = field(default_factory=Beta002Strategy)
    log_max_mb: int = DEFAULT_POSITION_MANAGER_LOG_MAX_MB

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

        position = self._open_position_for_plan(plan)
        if position is None:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=plan.ticket,
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
        if self._is_duplicate_beta_execution(plan, decision):
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="DUPLICATE_DECISION_BLOCKED",
                    action="STOP_MAINTAINED",
                    message="Decisao Beta ja executada para este candle/estado; acao duplicada bloqueada.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=decision.requested_stop,
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
                    audit_tags=("DUPLICATE_DECISION_BLOCKED",),
                    **self._beta_result_fields(decision),
                )
            )
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
                    missing_data=decision.missing_data,
                    audit_tags=("HOLD_POSITION", decision.state),
                    **self._beta_result_fields(decision),
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
                    **self._beta_result_fields(decision),
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
                    **self._beta_result_fields(decision),
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
                    **self._beta_result_fields(decision),
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
                    **self._beta_result_fields(decision),
                )
            )

        response = self.provider.modify_position_sl(plan.symbol, ticket, candidate)
        success = bool(getattr(response, "success", False) or getattr(response, "accepted", False))
        provider_message = str(getattr(response, "message", "") or "SL enviado ao MT5.")
        result = PositionManagerResult(
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
            **self._beta_result_fields(decision),
        )
        if success:
            self._mark_beta_execution(plan, decision)
        return self._record(
            result
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

    def _open_position_for_plan(self, plan: PositionTradePlan) -> object | None:
        """Busca a posicao exata por ticket quando o plano veio de ordem aceita."""
        if plan.ticket is not None:
            lookup = getattr(self.provider, "get_open_position_by_ticket", None)
            if callable(lookup):
                return lookup(plan.symbol, int(plan.ticket))
        position = self.provider.get_open_position(plan.symbol)
        if plan.ticket is not None and position is not None:
            position_ticket = _optional_int(getattr(position, "ticket", None))
            if position_ticket is not None and position_ticket != int(plan.ticket):
                return None
        return position

    def _decide(
        self,
        plan: PositionTradePlan,
        snapshot: PositionStateSnapshot,
    ) -> PositionManagerDecision:
        if _normalize_beta_id(plan.beta_id) == BETA002_ID:
            return self._decide_beta002(plan, snapshot)
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
        if (
            self.early_exit_enabled
            and snapshot.r_multiple >= self._early_exit_activation_r(plan)
            and self._early_exit_confirmed(snapshot)
        ):
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
        if snapshot.r_multiple < 1.00:
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason=(
                    "Trade ainda nao andou 1.00R a favor; preservar stop inicial "
                    "e dar espaco ao plano do Lab."
                ),
                confidence=0.55,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence + ("PROTECTION_WAIT_UNDER_1_00R",),
            )
        protection_activation_r = self._protection_activation_r(plan)
        if snapshot.r_multiple < protection_activation_r:
            return PositionManagerDecision(
                symbol=plan.symbol,
                ticket=snapshot.ticket,
                state=snapshot.state,
                action="HOLD_POSITION",
                reason=(
                    f"Trade entre 1.00R e {protection_activation_r:.2f}R; "
                    "Position Manager observa, mas nao move SL antes de maturacao "
                    "suficiente do plano."
                ),
                confidence=0.55,
                beta_id=plan.beta_id,
                beta_version=plan.beta_version,
                beta_mode=plan.beta_mode,
                evidence=snapshot.evidence
                + (f"PROTECTION_WAIT_UNDER_{_r_tag(protection_activation_r)}R",),
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

    def _decide_beta002(
        self,
        plan: PositionTradePlan,
        snapshot: PositionStateSnapshot,
    ) -> PositionManagerDecision:
        """Avalia BETA002 somente para planos explicitamente selecionados."""
        state = self._load_beta_state()
        key = self._beta_state_key(plan, snapshot.ticket)
        previous = state.get(key, {}) if isinstance(state.get(key), dict) else {}
        candles = tuple(
            self.provider.get_recent_candles(
                plan.symbol,
                self.beta002_strategy.config.timeframe,
                max(
                    self.beta002_strategy.config.minimum_candles
                    + self.beta002_strategy.config.ema_period
                    + 5,
                    40,
                ),
            )
            or ()
        )
        context = BetaStrategyContext(
            symbol=plan.symbol,
            ticket=snapshot.ticket,
            side=snapshot.side,
            volume=snapshot.volume,
            entry_price=snapshot.entry_price,
            current_price=snapshot.current_price,
            current_stop=snapshot.current_stop,
            current_target=snapshot.current_target,
            current_r=snapshot.r_multiple,
            candles=candles,
            position_open=True,
            candle_closed=len(candles) >= 2,
            evaluated_at=datetime.now().astimezone().isoformat(),
            previous_state=str(previous.get("state") or "N/D"),
            previous_confirmation_count=int(previous.get("confirmation_count") or 0),
            previous_state_duration=int(previous.get("state_duration") or 0),
            previous_action_key=str(previous.get("last_action_key") or "N/D"),
            stop_management_parameters=plan.stop_management_parameters,
        )
        beta_decision = self.beta002_strategy.evaluate(context)
        self._save_beta_state(
            key,
            {
                **previous,
                "state": beta_decision.raw_state,
                "confirmation_count": beta_decision.confirmation_count,
                "state_duration": beta_decision.state_duration,
                "last_evaluated_at": beta_decision.evaluated_at,
                "last_strength_score": beta_decision.strength_score,
                "last_evidence": list(beta_decision.evidence),
            },
        )
        action = beta_decision.action
        allowed = self.assisted_execution_enabled
        return PositionManagerDecision(
            symbol=plan.symbol,
            ticket=snapshot.ticket,
            state=beta_decision.state,
            action=action,
            reason=beta_decision.reason,
            confidence=beta_decision.confidence,
            beta_id=beta_decision.beta_id,
            beta_version=beta_decision.beta_version,
            beta_mode=plan.beta_mode,
            allowed_to_execute=allowed,
            execution_mode="AUTOMATIC_DEMO" if allowed else "READ_ONLY",
            requested_stop=beta_decision.candidate_stop,
            requested_close_volume=snapshot.volume if action == "FULL_EXIT" else None,
            final_exit_reason=beta_decision.final_exit_reason,
            evidence=snapshot.evidence + beta_decision.evidence,
            strength_score=beta_decision.strength_score,
            confirmation_count=beta_decision.confirmation_count,
            state_duration=beta_decision.state_duration,
            ema14_value=beta_decision.ema14_value,
            ema14_slope=beta_decision.ema14_slope,
            momentum_14=beta_decision.momentum_14,
            atr_14=beta_decision.atr_14,
            atr_relative_change=beta_decision.atr_relative_change,
            structure_signal=beta_decision.structure_signal,
            evaluated_at=beta_decision.evaluated_at,
            beta_closed_candle_time=beta_decision.closed_candle_time,
            missing_data=beta_decision.missing_data,
        )

    def _runtime_policy(self, plan: PositionTradePlan) -> str:
        """Mantem compatibilidade com campo legado sem predefinir a saida."""
        raw_policy = str(plan.stop_management or "DYNAMIC_POSITION_MANAGER").upper()
        if raw_policy in {"", "N/D", "FIXED_STOP"}:
            return "DYNAMIC_POSITION_MANAGER"
        return raw_policy

    def _plan_risk_reward(self, plan: PositionTradePlan) -> float | None:
        configured = _positive_float(plan.risk_reward)
        if configured is not None:
            return configured
        return _risk_reward_from_prices(plan.entry, plan.stop, plan.target)

    def _is_rr3_plan(self, plan: PositionTradePlan) -> bool:
        rr = self._plan_risk_reward(plan)
        return rr is not None and rr >= 2.95

    def _protection_activation_r(self, plan: PositionTradePlan) -> float:
        # Evita saida/protecao cedo demais: RR3 precisa respirar; planos menores
        # tambem aguardam maturacao minima antes de mover SL.
        return 1.50

    def _early_exit_activation_r(self, plan: PositionTradePlan) -> float:
        return 2.00 if self._is_rr3_plan(plan) else 1.50

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
        if snapshot.r_multiple < self._protection_activation_r(plan):
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
                    **self._beta_result_fields(decision),
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
        result = PositionManagerResult(
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
            **self._beta_result_fields(decision),
        )
        if success:
            self._mark_beta_execution(plan, decision)
        return self._record(
            result
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

    def _beta_result_fields(
        self,
        decision: PositionManagerDecision,
    ) -> dict[str, Any]:
        return {
            "beta_strength_score": decision.strength_score,
            "beta_confirmation_count": decision.confirmation_count,
            "beta_state_duration": decision.state_duration,
            "beta_ema14_value": decision.ema14_value,
            "beta_ema14_slope": decision.ema14_slope,
            "beta_momentum_14": decision.momentum_14,
            "beta_atr_14": decision.atr_14,
            "beta_atr_relative_change": decision.atr_relative_change,
            "beta_structure_signal": decision.structure_signal,
            "beta_evaluated_at": decision.evaluated_at,
            "beta_closed_candle_time": decision.beta_closed_candle_time,
        }

    def _beta_state_key(self, plan: PositionTradePlan, ticket: int) -> str:
        return f"{_normalize_beta_id(plan.beta_id)}:{plan.symbol}:{int(ticket or 0)}"

    def _beta_action_key(
        self,
        plan: PositionTradePlan,
        decision: PositionManagerDecision,
    ) -> str:
        candidate = (
            "NONE"
            if decision.requested_stop is None
            else f"{float(decision.requested_stop):.8f}"
        )
        return "|".join(
            [
                _normalize_beta_id(plan.beta_id),
                plan.symbol,
                str(decision.ticket),
                decision.action,
                decision.state,
                candidate,
                str(plan.candle_time or "N/D"),
            ]
        )

    def _is_duplicate_beta_execution(
        self,
        plan: PositionTradePlan,
        decision: PositionManagerDecision,
    ) -> bool:
        if _normalize_beta_id(plan.beta_id) != BETA002_ID:
            return False
        if decision.action not in {"PROTECT_POSITION", "FULL_EXIT"}:
            return False
        state = self._load_beta_state()
        key = self._beta_state_key(plan, decision.ticket)
        current = state.get(key, {}) if isinstance(state.get(key), dict) else {}
        return str(current.get("last_action_key") or "") == self._beta_action_key(
            plan, decision
        )

    def _mark_beta_execution(
        self,
        plan: PositionTradePlan,
        decision: PositionManagerDecision,
    ) -> None:
        if _normalize_beta_id(plan.beta_id) != BETA002_ID:
            return
        state = self._load_beta_state()
        key = self._beta_state_key(plan, decision.ticket)
        current = state.get(key, {}) if isinstance(state.get(key), dict) else {}
        self._save_beta_state(
            key,
            {
                **current,
                "last_action_key": self._beta_action_key(plan, decision),
                "last_action": decision.action,
                "last_action_at": datetime.now().astimezone().isoformat(),
                "last_candidate_stop": decision.requested_stop,
                "last_state": decision.state,
            },
        )

    def _load_beta_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_beta_state(self, key: str, value: dict[str, Any]) -> None:
        state = self._load_beta_state()
        state[key] = value
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _record(self, result: PositionManagerResult) -> PositionManagerResult:
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "type": "POSITION_MANAGER",
            **result.__dict__,
        }
        previous = self._current_state_record(payload)
        self._write_current_state(payload)
        should_append = self._should_append_history(payload, previous)
        if should_append and self._is_low_signal_history_duplicate(payload):
            should_append = False
        if should_append:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_history_if_needed()
            with self.log_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=True) + "\n")
            self._remember_low_signal_history(payload)
        return result

    def _rotate_history_if_needed(self) -> None:
        """Arquiva o JSONL quente quando crescer demais para preservar leveza."""
        if not self.log_path.exists():
            return
        max_mb = _positive_int(
            os.getenv("TRADERIA_POSITION_MANAGER_LOG_MAX_MB"),
            self.log_max_mb,
        )
        max_bytes = max(1, max_mb) * 1024 * 1024
        try:
            if self.log_path.stat().st_size <= max_bytes:
                return
            stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
            archive_path = self.log_path.with_name(
                f"{self.log_path.stem}_{stamp}.archive{self.log_path.suffix}"
            )
            self.log_path.replace(archive_path)
        except OSError:
            return

    def _current_state_record(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        state = self._load_current_state()
        records = state.get("records")
        if not isinstance(records, dict):
            return None
        for key in self._current_state_keys(payload):
            record = records.get(key)
            if isinstance(record, dict):
                return record
        return None

    def _load_current_state(self) -> dict[str, Any]:
        if not self.current_state_path.exists():
            return {}
        try:
            payload = json.loads(self.current_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_current_state(self, payload: dict[str, Any]) -> None:
        state = self._load_current_state()
        records = state.get("records")
        if not isinstance(records, dict):
            records = {}
        for key in self._current_state_keys(payload):
            records[key] = payload
        state = {
            "updated_at": payload.get("timestamp"),
            "type": "POSITION_MANAGER_CURRENT",
            "records": records,
        }
        self.current_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_state_path.write_text(
            json.dumps(state, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _current_state_keys(self, payload: dict[str, Any]) -> list[str]:
        keys: list[str] = []
        ticket = payload.get("ticket")
        if ticket is not None:
            keys.append(f"ticket:{ticket}")
        symbol = str(payload.get("symbol") or "").upper()
        if symbol:
            keys.append(f"symbol:{symbol}")
        return keys

    def _should_append_history(
        self,
        payload: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> bool:
        if self._is_high_signal_history(payload):
            return True
        if previous is None:
            return True
        return self._history_signature(payload) != self._history_signature(previous)

    def _is_high_signal_history(self, payload: dict[str, Any]) -> bool:
        status = str(payload.get("status") or "").upper()
        action = str(payload.get("action") or "").upper()
        execution_status = str(payload.get("execution_status") or "").upper()
        final_reason = str(payload.get("final_exit_reason") or "").upper()
        tags = {str(tag).upper() for tag in payload.get("audit_tags", []) or []}
        return (
            bool(payload.get("submitted"))
            or bool(payload.get("success"))
            or payload.get("new_stop") is not None
            or execution_status in {"EXECUTED", "REJECTED", "FAILED"}
            or action in {"STOP_MOVED", "EARLY_EXIT", "FULL_EXIT"}
            or status in {
                "STOP_MOVED",
                "POSITION_CLOSED",
                "CLOSE_REJECTED",
                "EXECUTION_DISABLED",
                "STOP_MOVE_BLOCKED_NOT_PROTECTIVE",
                "STOP_MOVE_BLOCKED_BY_MARKET",
                "DUPLICATE_DECISION_BLOCKED",
            }
            or final_reason not in {"", "N/D", "NONE"}
            or bool(
                tags
                & {
                    "EARLY_EXIT_CANDIDATE",
                    "FULL_EXIT_EXECUTED",
                    "FULL_EXIT_REJECTED",
                    "STOP_MOVED",
                    "STOP_MOVE_CANDIDATE",
                    "STOP_MOVE_BLOCKED_BY_CONFIG",
                }
            )
        )

    def _is_low_signal_history_duplicate(self, payload: dict[str, Any]) -> bool:
        if self._is_high_signal_history(payload):
            return False
        dedupe = self._load_history_dedupe()
        key = self._history_dedupe_key(payload)
        signature = self._history_signature_text(payload)
        return bool(key and dedupe.get(key) == signature)

    def _remember_low_signal_history(self, payload: dict[str, Any]) -> None:
        if self._is_high_signal_history(payload):
            return
        key = self._history_dedupe_key(payload)
        if not key:
            return
        dedupe = self._load_history_dedupe()
        dedupe[key] = self._history_signature_text(payload)
        history_dedupe_path = self._resolved_history_dedupe_path()
        history_dedupe_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            history_dedupe_path.write_text(
                json.dumps(dedupe, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    def _load_history_dedupe(self) -> dict[str, str]:
        history_dedupe_path = self._resolved_history_dedupe_path()
        if not history_dedupe_path.exists():
            return {}
        try:
            payload = json.loads(
                history_dedupe_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(key, str)
        } if isinstance(payload, dict) else {}

    def _resolved_history_dedupe_path(self) -> Path:
        default_path = Path(".traderia") / "position_manager_history_dedupe.json"
        if (
            self.history_dedupe_path == default_path
            and self.log_path.parent != default_path.parent
        ):
            return self.log_path.with_name("position_manager_history_dedupe.json")
        return self.history_dedupe_path

    def _history_dedupe_key(self, payload: dict[str, Any]) -> str:
        ticket = payload.get("ticket")
        if ticket is not None:
            return f"ticket:{ticket}"
        symbol = str(payload.get("symbol") or "").upper()
        side = str(payload.get("side") or "").upper()
        policy = str(payload.get("policy") or "").upper()
        beta_id = str(payload.get("beta_id") or "").upper()
        return f"symbol:{symbol}:{side}:{policy}:{beta_id}" if symbol else ""

    def _history_signature_text(self, payload: dict[str, Any]) -> str:
        return json.dumps(
            self._history_signature(payload),
            ensure_ascii=True,
            default=str,
        )

    def _history_signature(self, record: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(record.get("symbol") or "").upper(),
            record.get("ticket"),
            str(record.get("status") or "").upper(),
            str(record.get("action") or "").upper(),
            str(record.get("position_state") or "").upper(),
            str(record.get("side") or "").upper(),
            str(record.get("policy") or "").upper(),
            str(record.get("beta_id") or "").upper(),
            str(record.get("beta_mode") or "").upper(),
            str(record.get("final_exit_reason") or "").upper(),
            tuple(record.get("missing_data") or ()),
            tuple(record.get("audit_tags") or ()),
        )

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


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return max(1, int(default))
    return max(1, parsed)


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    try:
        return int(value)
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


def _risk_reward_from_prices(
    entry: float,
    stop: float,
    target: float | None,
) -> float | None:
    if target is None:
        return None
    risk = abs(float(entry) - float(stop))
    reward = abs(float(target) - float(entry))
    if risk <= 0.0 or reward <= 0.0:
        return None
    return reward / risk


def _r_tag(value: float) -> str:
    return f"{value:.2f}".replace(".", "_")


def _normalize_beta_id(value: object) -> str:
    normalized = str(value or DEFAULT_BETA_ID).strip().upper()
    if normalized == "LEGACY_CURRENT_EXIT":
        return DEFAULT_BETA_ID
    return normalized or DEFAULT_BETA_ID
