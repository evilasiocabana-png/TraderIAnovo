"""Pre-autorizador read-only do Moving Average Exit dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitMovingAverageAuthorizer:
    """Avalia elegibilidade para Moving Average Exit sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()

        if policy != "MOVING_AVERAGE_EXIT" or action != "TIGHTEN_BY_MOMENTUM_LOSS":
            return self._rejected(
                policy,
                action,
                reading,
                "Somente MOVING_AVERAGE_EXIT com acao TIGHTEN_BY_MOMENTUM_LOSS entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                "Sem posicao aberta; Moving Average Exit nao pode ser elegivel.",
            )
        if reading.state not in {"REVERSAL_RISK", "TIME_DECAY", "PROTECTED_POSITION"}:
            return self._rejected(
                policy,
                action,
                reading,
                "Moving Average Exit exige perda de tendencia, reversao ou posicao protegida nesta fase.",
            )

        side = str(reading.side or "").upper()
        current_price = reading.current_price
        entry_price = reading.entry_price
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                "Direcao da posicao invalida para validar Moving Average Exit.",
            )
        if current_price is None or entry_price is None:
            return self._rejected(
                policy,
                action,
                reading,
                "Preco atual ou entrada ausente.",
            )
        if reading.r_multiple < -0.25:
            return self._rejected(
                policy,
                action,
                reading,
                "Moving Average Exit nao deve confirmar saida dinamica em perda ja deteriorada nesta fase.",
            )
        if not self._has_momentum_against(reading):
            return self._rejected(
                policy,
                action,
                reading,
                "Momentum ainda nao confirma perda de tendencia.",
            )
        if recommendation.confidence < 0.55:
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
                "Elegivel para futura autorizacao demo de Moving Average Exit; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=None,
            market_state=reading.state,
            source="DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_AUTHORIZER",
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
            source="DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_AUTHORIZER",
        )

    def _has_momentum_against(self, reading: DynamicExitMarketReading) -> bool:
        momentum = reading.momentum
        if momentum is None:
            return False
        if str(reading.side or "").upper() == "SELL":
            return momentum > 0
        return momentum < 0
