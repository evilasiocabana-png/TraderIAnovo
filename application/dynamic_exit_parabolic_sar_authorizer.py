"""Pre-autorizador read-only do Parabolic SAR dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitParabolicSarAuthorizer:
    """Avalia elegibilidade para Parabolic SAR sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()

        if policy != "PARABOLIC_SAR" or action != "TIGHTEN_BY_MOMENTUM_LOSS":
            return self._rejected(
                policy,
                action,
                reading,
                "Somente PARABOLIC_SAR com acao TIGHTEN_BY_MOMENTUM_LOSS entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                "Sem posicao aberta; Parabolic SAR nao pode ser elegivel.",
            )
        if reading.state not in {"REVERSAL_RISK", "PROTECTED_POSITION"}:
            return self._rejected(
                policy,
                action,
                reading,
                "Parabolic SAR exige risco de reversao rapida ou posicao ja protegida nesta fase.",
            )

        side = str(reading.side or "").upper()
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                "Direcao da posicao invalida para validar Parabolic SAR.",
            )
        if reading.current_price is None or reading.stop_price is None:
            return self._rejected(
                policy,
                action,
                reading,
                "Preco atual ou stop atual ausente.",
            )
        if recommendation.candidate_stop is None:
            return self._rejected(
                policy,
                action,
                reading,
                "Parabolic SAR exige stop candidato auditavel.",
            )
        if reading.r_multiple < -0.15:
            return self._rejected(
                policy,
                action,
                reading,
                "Parabolic SAR nao deve confirmar ajuste em perda deteriorada nesta fase.",
            )
        if not self._has_momentum_against(reading):
            return self._rejected(
                policy,
                action,
                reading,
                "Momentum ainda nao confirma reversao rapida contra a posicao.",
            )
        if not self._candidate_improves_protection(reading, recommendation.candidate_stop):
            return self._rejected(
                policy,
                action,
                reading,
                "Stop candidato nao melhora a protecao ou esta do lado errado do mercado.",
            )
        if recommendation.confidence < 0.57:
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
                "Elegivel para futura autorizacao demo de Parabolic SAR; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=recommendation.candidate_stop,
            market_state=reading.state,
            source="DYNAMIC_EXIT_PARABOLIC_SAR_DEMO_AUTHORIZER",
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
            source="DYNAMIC_EXIT_PARABOLIC_SAR_DEMO_AUTHORIZER",
        )

    def _has_momentum_against(self, reading: DynamicExitMarketReading) -> bool:
        momentum = reading.momentum
        if momentum is None:
            return False
        if str(reading.side or "").upper() == "SELL":
            return momentum > 0
        return momentum < 0

    def _candidate_improves_protection(
        self,
        reading: DynamicExitMarketReading,
        candidate_stop: float,
    ) -> bool:
        current_price = reading.current_price
        current_stop = reading.stop_price
        if current_price is None or current_stop is None:
            return False

        if str(reading.side or "").upper() == "SELL":
            return candidate_stop < current_stop and candidate_stop > current_price
        return candidate_stop > current_stop and candidate_stop < current_price
