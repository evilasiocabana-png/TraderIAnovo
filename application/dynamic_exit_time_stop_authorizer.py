"""Pre-autorizador read-only do Time Stop dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitTimeStopAuthorizer:
    """Avalia elegibilidade para Time Stop sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()

        if policy != "TIME_STOP" or action != "TIME_DECAY_EXIT_WATCH":
            return self._rejected(
                policy,
                action,
                reading,
                "Somente TIME_STOP com acao TIME_DECAY_EXIT_WATCH entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                "Sem posicao aberta; Time Stop nao pode ser elegivel.",
            )
        if reading.state != "TIME_DECAY":
            return self._rejected(
                policy,
                action,
                reading,
                "Time Stop exige estado TIME_DECAY nesta fase.",
            )

        side = str(reading.side or "").upper()
        current_price = reading.current_price
        entry_price = reading.entry_price
        minutes = reading.time_in_position_minutes
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                "Direcao da posicao invalida para validar Time Stop.",
            )
        if current_price is None or entry_price is None or minutes is None:
            return self._rejected(
                policy,
                action,
                reading,
                "Preco atual, entrada ou tempo em posicao ausente.",
            )
        if minutes < 240:
            return self._rejected(
                policy,
                action,
                reading,
                "Time Stop exige pelo menos 240 minutos em posicao nesta fase.",
            )
        if abs(reading.r_multiple) > 0.25:
            return self._rejected(
                policy,
                action,
                reading,
                "Time Stop exige operacao sem progresso relevante em R.",
            )
        if self._has_favorable_momentum(reading):
            return self._rejected(
                policy,
                action,
                reading,
                "Momentum ainda favorece a posicao; Time Stop nao deve ser elegivel.",
            )
        if recommendation.confidence < 0.45:
            return self._rejected(
                policy,
                action,
                reading,
                "Confianca insuficiente para pre-autorizacao demo.",
            )

        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="ELIGIBLE_READ_ONLY",
            reason=(
                "Elegivel para futura autorizacao demo de Time Stop; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=None,
            market_state=reading.state,
            source="DYNAMIC_EXIT_TIME_STOP_DEMO_AUTHORIZER",
        )

    def _rejected(
        self,
        policy: str,
        action: str,
        reading: DynamicExitMarketReading,
        reason: str,
    ) -> DynamicExitDemoAuthorization:
        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="REJECTED",
            reason=reason,
            eligible_to_authorize=False,
            allowed_to_execute_demo=False,
            candidate_stop=None,
            market_state=reading.state,
            source="DYNAMIC_EXIT_TIME_STOP_DEMO_AUTHORIZER",
        )

    def _has_favorable_momentum(self, reading: DynamicExitMarketReading) -> bool:
        momentum = reading.momentum
        if momentum is None:
            return False
        if str(reading.side or "").upper() == "SELL":
            return momentum < 0
        return momentum > 0
