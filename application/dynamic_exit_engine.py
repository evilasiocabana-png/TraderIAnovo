"""Motor unificado read-only de saida dinamica."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from application.dynamic_exit_atr_trailing_authorizer import (
    DynamicExitAtrTrailingAuthorizer,
)
from application.dynamic_exit_break_even_authorizer import (
    DynamicExitBreakEvenAuthorizer,
)
from application.dynamic_exit_chandelier_authorizer import (
    DynamicExitChandelierAuthorizer,
)
from application.dynamic_exit_donchian_authorizer import (
    DynamicExitDonchianAuthorizer,
)
from application.dynamic_exit_market_state_service import (
    DynamicExitMarketStateClassifier,
)
from application.dynamic_exit_moving_average_authorizer import (
    DynamicExitMovingAverageAuthorizer,
)
from application.dynamic_exit_parabolic_sar_authorizer import (
    DynamicExitParabolicSarAuthorizer,
)
from application.dynamic_exit_recommendation_service import (
    DynamicExitRecommendationEngine,
)
from application.dynamic_exit_time_stop_authorizer import (
    DynamicExitTimeStopAuthorizer,
)
from application.dynamic_exit_volatility_authorizer import (
    DynamicExitVolatilityAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)
from domain.contracts.dynamic_exit_engine import (
    DynamicExitEngineInput,
    DynamicExitEngineResult,
)


class DynamicExitAuthorizer(Protocol):
    """Contrato minimo dos autorizadores read-only."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        """Avalia pre-autorizacao sem executar."""


class DynamicExitUnifiedEngine:
    """Orquestra leitura, recomendacao e pre-autorizacao sem executar."""

    def __init__(
        self,
        *,
        classifier: DynamicExitMarketStateClassifier | None = None,
        recommender: DynamicExitRecommendationEngine | None = None,
        authorizers: dict[str, DynamicExitAuthorizer] | None = None,
    ) -> None:
        self._classifier = classifier or DynamicExitMarketStateClassifier()
        self._recommender = recommender or DynamicExitRecommendationEngine()
        self._authorizers = authorizers or self._default_authorizers()

    def evaluate(self, payload: DynamicExitEngineInput) -> DynamicExitEngineResult:
        """Retorna a decisao dinamica unificada em modo read-only."""

        policy = str(payload.policy or "FIXED_STOP").upper()
        market_reading = self._classifier.classify(payload.reading)
        recommendation = payload.recommendation or self._recommender.recommend(
            market_reading,
            policy=policy,
            plan_status=payload.plan_status,
        )
        recommendation = self._normalize_recommendation(recommendation, market_reading)
        authorization = self._authorize(policy, market_reading, recommendation)

        return DynamicExitEngineResult(
            policy=policy,
            market_reading=market_reading,
            recommendation=recommendation,
            authorization=authorization,
            allowed_to_execute_demo=False,
        )

    def _authorize(
        self,
        policy: str,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        authorizer = self._authorizers.get(policy)
        if authorizer is None:
            return DynamicExitDemoAuthorization(
                policy=policy,
                action=recommendation.action,
                status="REJECTED",
                reason="Politica sem autorizador demo registrado no motor unificado.",
                eligible_to_authorize=False,
                allowed_to_execute_demo=False,
                candidate_stop=recommendation.candidate_stop,
                market_state=reading.state,
                source="DYNAMIC_EXIT_UNIFIED_ENGINE_FALLBACK",
            )
        authorization = authorizer.authorize(reading, recommendation)
        if authorization.allowed_to_execute_demo:
            return replace(authorization, allowed_to_execute_demo=False)
        return authorization

    def _normalize_recommendation(
        self,
        recommendation: DynamicExitRecommendation,
        reading: DynamicExitMarketReading,
    ) -> DynamicExitRecommendation:
        return replace(
            recommendation,
            market_state=reading.state,
            r_multiple=reading.r_multiple,
            allowed_to_execute_demo=False,
        )

    def _default_authorizers(self) -> dict[str, DynamicExitAuthorizer]:
        return {
            "ATR_TRAILING_STOP": DynamicExitAtrTrailingAuthorizer(),
            "BREAK_EVEN": DynamicExitBreakEvenAuthorizer(),
            "CHANDELIER_EXIT": DynamicExitChandelierAuthorizer(),
            "DONCHIAN_CHANNEL_STOP": DynamicExitDonchianAuthorizer(),
            "MOVING_AVERAGE_EXIT": DynamicExitMovingAverageAuthorizer(),
            "PARABOLIC_SAR": DynamicExitParabolicSarAuthorizer(),
            "TIME_STOP": DynamicExitTimeStopAuthorizer(),
            "VOLATILITY_STOP": DynamicExitVolatilityAuthorizer(),
        }
