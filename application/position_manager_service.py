"""Position Manager para acompanhar SL de posicoes MT5 Demo abertas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from application.demo_execution_service import DisabledDemoExecutionProvider


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
    atr: float | None = None
    momentum: float | None = None
    volatility: float | None = None
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
            atr=atr,
            momentum=momentum,
            volatility=volatility,
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
    atr: float | None = None
    candle_time: str = "N/D"
    missing_data: tuple[str, ...] = ()
    audit_tags: tuple[str, ...] = ()
    submitted: bool = False
    success: bool = False


@dataclass
class PositionManagerService:
    """Acompanha posicoes abertas sem abrir novas entradas."""

    provider: PositionManagerProvider = field(
        default_factory=DisabledDemoExecutionProvider
    )
    assisted_execution_enabled: bool = False
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
                        status="PLAN_ABSENT",
                        action="STOP_MAINTAINED",
                        message="Plano valido ausente ou incompleto; SL preservado.",
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
                    status="PLAN_ABSENT",
                    action="STOP_MAINTAINED",
                    message="Plano do Lab nao esta valido; SL preservado.",
                    policy=plan.stop_management,
                    side=plan.side,
                    candle_time=plan.candle_time,
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
                    side=plan.side,
                    candle_time=plan.candle_time,
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
                    status="READ_ERROR",
                    action="STOP_MAINTAINED",
                    message="Stop atual ausente na posicao MT5; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    candle_time=plan.candle_time,
                )
            )
        current_price = self.provider.get_current_price(plan.symbol)
        if current_price is None:
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="READ_ERROR",
                    action="STOP_MAINTAINED",
                    message="Preco atual ausente; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    candle_time=plan.candle_time,
                )
            )

        candidate = self._candidate_stop(
            side=side,
            entry=entry,
            current_stop=current_stop,
            current_price=float(current_price),
            plan=plan,
        )
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
                    atr=plan.atr,
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
                    status="STOP_MAINTAINED",
                    action="STOP_MAINTAINED",
                    message="Stop candidato nao melhora o risco; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=candidate,
                    current_price=float(current_price),
                    atr=plan.atr,
                    candle_time=plan.candle_time,
                    audit_tags=("STOP_MOVE_BLOCKED_NOT_PROTECTIVE",),
                )
            )
        if not self._is_stop_before_market(side, candidate, float(current_price)):
            return self._record(
                PositionManagerResult(
                    symbol=plan.symbol,
                    ticket=ticket,
                    status="STOP_MAINTAINED",
                    action="STOP_MAINTAINED",
                    message="Stop candidato cruza ou encosta no preco atual; SL preservado.",
                    policy=plan.stop_management,
                    side=side,
                    old_stop=current_stop,
                    new_stop=candidate,
                    current_price=float(current_price),
                    atr=plan.atr,
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
                    atr=plan.atr,
                    candle_time=plan.candle_time,
                    execution_status="BLOCKED_BY_CONFIG",
                    audit_tags=("STOP_MOVE_CANDIDATE", "STOP_MOVE_BLOCKED_BY_CONFIG"),
                )
            )

        response = self.provider.modify_position_sl(plan.symbol, ticket, candidate)
        success = bool(getattr(response, "success", False) or getattr(response, "accepted", False))
        return self._record(
            PositionManagerResult(
                symbol=plan.symbol,
                ticket=ticket,
                status="STOP_MOVED" if success else "MODIFY_REJECTED",
                action="STOP_MOVED" if success else "STOP_MAINTAINED",
                message=str(getattr(response, "message", "") or "SL enviado ao MT5."),
                policy=plan.stop_management,
                side=side,
                old_stop=current_stop,
                new_stop=candidate,
                current_price=float(current_price),
                atr=plan.atr,
                candle_time=plan.candle_time,
                execution_mode="AUTOMATIC_DEMO",
                execution_status="EXECUTED" if success else "BLOCKED",
                audit_tags=("STOP_MOVED" if success else "STOP_MOVE_FAILED",),
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
        if plan.stop_management == "ATR_TRAILING_STOP" and plan.atr is None:
            return "ATR_ABSENT", "ATR ausente para trailing; SL preservado.", ("atr",)
        if (
            plan.stop_management == "VOLATILITY_STOP_PROTECTION"
            and (plan.atr is None or plan.volatility is None)
        ):
            missing = tuple(
                name
                for name, value in (("atr", plan.atr), ("volatility", plan.volatility))
                if value is None
            )
            return "MARKET_DATA_ABSENT", "Dados de volatilidade ausentes; SL preservado.", missing
        if (
            plan.stop_management == "MOMENTUM_WEAKNESS_STOP_TIGHTENING"
            and plan.momentum is None
        ):
            return "MARKET_DATA_ABSENT", "Momentum ausente; SL preservado.", ("momentum",)
        if plan.stop_management == "STRUCTURE_BASED_STOP_PROTECTION" and not any(
            value is not None
            for value in (plan.support, plan.resistance, plan.swing_high, plan.swing_low)
        ):
            return "STRUCTURE_ABSENT", "Estrutura ausente; SL preservado.", ("structure",)
        if plan.stop_management not in {
            "BREAK_EVEN",
            "ATR_TRAILING_STOP",
            "MARKET_AWARE_STOP_PROTECTION",
            "VOLATILITY_STOP_PROTECTION",
            "MOMENTUM_WEAKNESS_STOP_TIGHTENING",
            "STRUCTURE_BASED_STOP_PROTECTION",
        }:
            return (
                "POLICY_BLOCKED_UNSUPPORTED_ACTION",
                "Politica sem acao MOVE_STOP segura suportada; SL preservado.",
                ("supported_policy",),
            )
        return "STOP_MAINTAINED", "Condicao segura nao atingida; SL preservado.", ()

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


def _non_negative_float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(parsed, 0.0)
