"""Simulacao paper de stop dinamico, sem modificar MT5."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_simulation import (
    DynamicExitSimulationDecision,
)


SIMULATABLE_DYNAMIC_EXIT_ACTIONS = {
    "PROTECT_TO_BREAK_EVEN",
    "TRAIL_BY_ATR",
    "TRAIL_BY_STRUCTURE",
    "TIGHTEN_BY_MOMENTUM_LOSS",
}


@dataclass
class DynamicExitSimulationService:
    """Aplica gates paper para stop dinamico sem execucao operacional."""

    min_stop_distance: float = 0.00001
    min_stop_delta: float = 0.00001
    max_spread_to_risk: float = 0.35
    decisions: list[DynamicExitSimulationDecision] = field(default_factory=list)
    _last_simulation_key: set[tuple[object, ...]] = field(default_factory=set)

    def simulate(
        self,
        *,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
        plan_status: str = "PLANO_VALIDO",
        enabled: bool = False,
        robot_armed: bool = False,
        ticket: int | None = None,
        candle_key: str = "N/D",
        atr_multiplier: float = 1.0,
    ) -> DynamicExitSimulationDecision:
        """Retorna decisao simulada e registra apenas quando habilitada."""

        action = str(recommendation.action or "KEEP_ORIGINAL_PLAN").upper()
        policy = str(recommendation.policy or "FIXED_STOP").upper()
        candidate = self._candidate_stop(
            reading=reading,
            recommendation=recommendation,
            action=action,
            atr_multiplier=atr_multiplier,
        )
        rejection_reasons = self._rejection_reasons(
            reading=reading,
            recommendation=recommendation,
            plan_status=plan_status,
            enabled=enabled,
            robot_armed=robot_armed,
            candidate_stop=candidate,
            action=action,
            candle_key=candle_key,
        )
        allowed = not rejection_reasons
        decision = DynamicExitSimulationDecision(
            symbol=reading.symbol,
            ticket=ticket,
            side=reading.side,
            policy=policy,
            action=action,
            current_stop=reading.stop_price,
            candidate_stop=candidate,
            approved_stop=candidate if allowed else None,
            allowed_to_simulate=allowed,
            rejection_reasons=tuple(rejection_reasons),
            market_state=reading.state,
            r_multiple=reading.r_multiple,
            created_at=datetime.now(timezone.utc).isoformat(),
            candle_key=candle_key,
        )
        if allowed:
            self._last_simulation_key.add(
                self._simulation_key(reading, action, candidate, candle_key)
            )
            self.decisions.append(decision)
        return decision

    def list_decisions(self) -> list[DynamicExitSimulationDecision]:
        """Lista decisoes paper registradas em memoria."""
        return list(self.decisions)

    def _candidate_stop(
        self,
        *,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
        action: str,
        atr_multiplier: float,
    ) -> float | None:
        if recommendation.candidate_stop is not None:
            return float(recommendation.candidate_stop)
        if reading.entry_price is None:
            return None
        side = str(reading.side or "").upper()
        if action == "PROTECT_TO_BREAK_EVEN":
            offset = max(self.min_stop_distance, float(reading.spread or 0.0))
            return (
                float(reading.entry_price) + offset
                if side == "BUY"
                else float(reading.entry_price) - offset
            )
        if action in {"TRAIL_BY_ATR", "TIGHTEN_BY_MOMENTUM_LOSS"}:
            if reading.atr is None:
                return None
            distance = max(float(reading.atr) * max(float(atr_multiplier), 0.1), self.min_stop_distance)
            if action == "TIGHTEN_BY_MOMENTUM_LOSS":
                distance = max(distance * 0.5, self.min_stop_distance)
            if reading.current_price is None:
                return None
            return (
                float(reading.current_price) - distance
                if side == "BUY"
                else float(reading.current_price) + distance
            )
        if action == "TRAIL_BY_STRUCTURE":
            return reading.candidate_stop
        return None

    def _rejection_reasons(
        self,
        *,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
        plan_status: str,
        enabled: bool,
        robot_armed: bool,
        candidate_stop: float | None,
        action: str,
        candle_key: str,
    ) -> list[str]:
        reasons: list[str] = []
        side = str(reading.side or "").upper()
        if not enabled:
            reasons.append("dynamic_exit_simulation_enabled desligado.")
        if not robot_armed:
            reasons.append("Robo demo/paper nao esta armado.")
        if not reading.is_positioned:
            reasons.append("Sem posicao aberta ou snapshot valido.")
        if side not in {"BUY", "SELL"}:
            reasons.append("Lado da posicao invalido.")
        if str(plan_status or "").upper() != "PLANO_VALIDO":
            reasons.append("Plano original do Lab nao esta PLANO_VALIDO.")
        if action == "TIME_DECAY_EXIT_WATCH":
            reasons.append("TIME_DECAY permanece apenas observacional nesta missao.")
        elif action not in SIMULATABLE_DYNAMIC_EXIT_ACTIONS:
            reasons.append("Acao dinamica nao simulavel nesta fase.")
        if action in {"TRAIL_BY_ATR", "TIGHTEN_BY_MOMENTUM_LOSS"} and reading.atr is None:
            reasons.append("ATR ausente para calcular stop candidato.")
        if candidate_stop is None:
            reasons.append("Stop candidato ausente.")
        if reading.current_price is None:
            reasons.append("Preco atual ausente.")
        if reading.stop_price is None:
            reasons.append("Stop atual ausente.")
        if reading.entry_price is None:
            reasons.append("Entrada ausente.")
        if candidate_stop is not None:
            reasons.extend(self._direction_rejections(reading, candidate_stop))
        if self._spread_excessive(reading):
            reasons.append("Spread excessivo em relacao ao risco.")
        if candidate_stop is not None and self._irrelevant_delta(reading, candidate_stop):
            reasons.append("Diferenca de stop irrelevante.")
        if (
            candidate_stop is not None
            and self._simulation_key(reading, action, candidate_stop, candle_key)
            in self._last_simulation_key
        ):
            reasons.append("Simulacao ja registrada para esta vela/janela.")
        if bool(recommendation.allowed_to_execute_demo):
            reasons.append("Recomendacao operacional foi normalizada para paper.")
        return reasons

    def _direction_rejections(
        self,
        reading: DynamicExitMarketReading,
        candidate_stop: float,
    ) -> list[str]:
        if reading.stop_price is None or reading.current_price is None:
            return []
        side = str(reading.side or "").upper()
        if side == "BUY":
            if candidate_stop <= float(reading.stop_price):
                return ["BUY nao pode simular stop para baixo ou igual ao atual."]
            if candidate_stop >= float(reading.current_price):
                return ["BUY exige stop candidato abaixo do preco atual."]
        if side == "SELL":
            if candidate_stop >= float(reading.stop_price):
                return ["SELL nao pode simular stop para cima ou igual ao atual."]
            if candidate_stop <= float(reading.current_price):
                return ["SELL exige stop candidato acima do preco atual."]
        return []

    def _spread_excessive(self, reading: DynamicExitMarketReading) -> bool:
        if reading.spread is None or reading.entry_price is None or reading.stop_price is None:
            return False
        risk = abs(float(reading.entry_price) - float(reading.stop_price))
        return risk > 0 and float(reading.spread) / risk > self.max_spread_to_risk

    def _irrelevant_delta(
        self,
        reading: DynamicExitMarketReading,
        candidate_stop: float,
    ) -> bool:
        if reading.stop_price is None:
            return False
        return abs(candidate_stop - float(reading.stop_price)) < self.min_stop_delta

    def _simulation_key(
        self,
        reading: DynamicExitMarketReading,
        action: str,
        candidate_stop: float | None,
        candle_key: str,
    ) -> tuple[object, ...]:
        return (
            str(reading.symbol).upper(),
            str(reading.side).upper(),
            action,
            candle_key,
            round(float(candidate_stop or 0.0), 8),
        )
