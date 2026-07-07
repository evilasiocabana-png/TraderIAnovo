"""Pre-autorizador read-only do break-even dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitBreakEvenAuthorizer:
    """Avalia elegibilidade para break-even dinamico sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()
        candidate_stop = recommendation.candidate_stop

        if policy != "BREAK_EVEN" or action != "PROTECT_TO_BREAK_EVEN":
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Somente BREAK_EVEN com acao PROTECT_TO_BREAK_EVEN entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Sem posicao aberta; break-even dinamico nao pode ser elegivel.",
            )
        if reading.state in {"NO_POSITION", "BAD_EXECUTION_CONTEXT", "TREND_RUNNER"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Estado de mercado nao permite break-even dinamico seguro nesta fase.",
            )

        side = str(reading.side or "").upper()
        current_price = reading.current_price
        entry_price = reading.entry_price
        current_stop = reading.stop_price
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Direcao da posicao invalida para validar break-even dinamico.",
            )
        if (
            current_price is None
            or entry_price is None
            or current_stop is None
            or candidate_stop is None
        ):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Preco, entrada, stop atual ou stop candidato ausente.",
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
        if recommendation.confidence < 0.50:
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
                "Elegivel para futura autorizacao demo de break-even; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=candidate_stop,
            market_state=reading.state,
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
