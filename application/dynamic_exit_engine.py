"""Motor unificado read-only de saida dinamica."""

from __future__ import annotations

from collections import OrderedDict
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
        max_cache_entries: int = 128,
    ) -> None:
        self._classifier = classifier or DynamicExitMarketStateClassifier()
        self._recommender = recommender or DynamicExitRecommendationEngine()
        self._authorizers = authorizers or self._default_authorizers()
        self._max_cache_entries = max(0, int(max_cache_entries))
        self._cache: OrderedDict[tuple[object, ...], DynamicExitEngineResult] = (
            OrderedDict()
        )

    def evaluate(self, payload: DynamicExitEngineInput) -> DynamicExitEngineResult:
        """Retorna a decisao dinamica unificada em modo read-only."""

        policy = str(payload.policy or "FIXED_STOP").upper()
        cache_key = self._cache_key(payload, policy)
        if cache_key is not None and cache_key in self._cache:
            result = self._cache.pop(cache_key)
            self._cache[cache_key] = result
            return result

        try:
            result = self._evaluate_uncached(payload, policy)
        except Exception as exc:  # noqa: BLE001 - runtime deve falhar fechado
            result = self._safe_error_result(payload.reading, policy, exc)

        if cache_key is not None:
            self._store_cache(cache_key, result)
        return result

    def _evaluate_uncached(
        self,
        payload: DynamicExitEngineInput,
        policy: str,
    ) -> DynamicExitEngineResult:
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

    def _cache_key(
        self,
        payload: DynamicExitEngineInput,
        policy: str,
    ) -> tuple[object, ...] | None:
        if self._max_cache_entries <= 0 or payload.recommendation is not None:
            return None
        reading = payload.reading
        return (
            policy,
            str(payload.plan_status or "SEM_PLANO").upper(),
            reading.symbol,
            reading.side,
            reading.is_positioned,
            reading.current_price,
            reading.entry_price,
            reading.stop_price,
            reading.target_price,
            reading.atr,
            reading.volatility,
            reading.momentum,
            reading.spread,
            reading.time_in_position_minutes,
            reading.state,
            reading.r_multiple,
            reading.candidate_stop,
        )

    def _store_cache(
        self,
        key: tuple[object, ...],
        result: DynamicExitEngineResult,
    ) -> None:
        self._cache[key] = result
        while len(self._cache) > self._max_cache_entries:
            self._cache.popitem(last=False)

    def _safe_error_result(
        self,
        reading: DynamicExitMarketReading,
        policy: str,
        exc: Exception,
    ) -> DynamicExitEngineResult:
        safe_reading = replace(
            reading,
            state="BAD_EXECUTION_CONTEXT",
            reason=f"Erro seguro no motor unificado: {exc.__class__.__name__}.",
            candidate_stop=reading.stop_price,
        )
        recommendation = DynamicExitRecommendation(
            policy=policy,
            action="NO_ACTION_BAD_CONTEXT",
            reason="Read-only: erro inesperado; manter plano original em fallback seguro.",
            confidence=0.0,
            market_state=safe_reading.state,
            r_multiple=safe_reading.r_multiple,
            candidate_stop=safe_reading.candidate_stop,
            allowed_to_execute_demo=False,
            source="DYNAMIC_EXIT_UNIFIED_ENGINE_SAFE_ERROR",
        )
        authorization = DynamicExitDemoAuthorization(
            policy=policy,
            action=recommendation.action,
            status="REJECTED",
            reason="Erro inesperado no motor unificado; execucao bloqueada.",
            eligible_to_authorize=False,
            allowed_to_execute_demo=False,
            candidate_stop=recommendation.candidate_stop,
            market_state=safe_reading.state,
            source="DYNAMIC_EXIT_UNIFIED_ENGINE_SAFE_ERROR",
        )
        return DynamicExitEngineResult(
            policy=policy,
            market_reading=safe_reading,
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
