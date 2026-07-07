"""Pre-autorizador read-only do ATR trailing dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitAtrTrailingAuthorizer:
    """Avalia elegibilidade para ATR trailing dinamico sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()
        candidate_stop = recommendation.candidate_stop

        if policy != "ATR_TRAILING_STOP" or action != "TRAIL_BY_ATR":
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Somente ATR_TRAILING_STOP com acao TRAIL_BY_ATR entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Sem posicao aberta; ATR trailing dinamico nao pode ser elegivel.",
            )
        if reading.state in {"NO_POSITION", "BAD_EXECUTION_CONTEXT", "NEW_POSITION"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Estado de mercado nao permite ATR trailing dinamico seguro nesta fase.",
            )

        side = str(reading.side or "").upper()
        current_price = reading.current_price
        entry_price = reading.entry_price
        current_stop = reading.stop_price
        atr = reading.atr
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Direcao da posicao invalida para validar ATR trailing dinamico.",
            )
        if (
            current_price is None
            or entry_price is None
            or current_stop is None
            or candidate_stop is None
            or atr is None
            or atr <= 0.0
        ):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Preco, entrada, stop atual, ATR ou stop candidato ausente.",
            )
        if not self._moved_in_favor(side, current_price, entry_price):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Posicao ainda nao andou a favor.",
            )
        if not self._improves_stop(side, candidate_stop, current_stop):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato nao melhora a protecao atual.",
            )
        if not self._stop_before_market(side, candidate_stop, current_price):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato ficaria do lado errado do mercado.",
            )
        if not self._respects_atr_noise(side, candidate_stop, current_price, atr):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato ignora ruido minimo do ATR.",
            )
        if reading.state == "REVERSAL_RISK" and not self._momentum_against(reading):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Risco de reversao sem perda de momentum confirmada.",
            )
        if recommendation.confidence < 0.55:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Confianca insuficiente para pre-autorizacao demo.",
            )

        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="ELIGIBLE_READ_ONLY",
            reason=(
                "Elegivel para futura autorizacao demo de ATR trailing; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=candidate_stop,
            market_state=reading.state,
            source="DYNAMIC_EXIT_ATR_TRAILING_DEMO_AUTHORIZER",
        )

    def _rejected(
        self,
        policy: str,
        action: str,
        reading: DynamicExitMarketReading,
        candidate_stop: float | None,
        reason: str,
    ) -> DynamicExitDemoAuthorization:
        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="REJECTED",
            reason=reason,
            eligible_to_authorize=False,
            allowed_to_execute_demo=False,
            candidate_stop=candidate_stop,
            market_state=reading.state,
            source="DYNAMIC_EXIT_ATR_TRAILING_DEMO_AUTHORIZER",
        )

    def _moved_in_favor(
        self,
        side: str,
        current_price: float,
        entry_price: float,
    ) -> bool:
        if side == "SELL":
            return current_price < entry_price
        return current_price > entry_price

    def _improves_stop(
        self,
        side: str,
        candidate_stop: float,
        current_stop: float,
    ) -> bool:
        epsilon = 1e-10
        if side == "SELL":
            return candidate_stop < current_stop - epsilon
        return candidate_stop > current_stop + epsilon

    def _stop_before_market(
        self,
        side: str,
        candidate_stop: float,
        current_price: float,
    ) -> bool:
        if side == "SELL":
            return candidate_stop > current_price
        return candidate_stop < current_price

    def _respects_atr_noise(
        self,
        side: str,
        candidate_stop: float,
        current_price: float,
        atr: float,
    ) -> bool:
        distance = (
            candidate_stop - current_price
            if side == "SELL"
            else current_price - candidate_stop
        )
        return distance >= atr * 0.25

    def _momentum_against(self, reading: DynamicExitMarketReading) -> bool:
        momentum = reading.momentum
        if momentum is None:
            return False
        if str(reading.side or "").upper() == "SELL":
            return momentum > 0
        return momentum < 0
