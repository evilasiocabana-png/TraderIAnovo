"""Avaliador de qualidade de contextos de mercado."""

from dataclasses import dataclass
from math import isfinite

from market.context.market_context import MarketContext


@dataclass(frozen=True)
class ContextQualityResult:
    """Resultado de qualidade dos contextos avaliados."""

    total_contexts: int
    confidence_score: float
    consistency_score: float
    quality_score: float


@dataclass(frozen=True)
class ContextQualityEngine:
    """Avalia consistencia de MarketContext sem reconstruir contexto."""

    def evaluate(
        self,
        contexts: tuple[MarketContext, ...],
    ) -> ContextQualityResult:
        """Retorna scores agregados dos contextos recebidos."""
        total_contexts = len(contexts)
        if total_contexts == 0:
            return ContextQualityResult(
                total_contexts=0,
                confidence_score=0.0,
                consistency_score=0.0,
                quality_score=0.0,
            )

        confidence_score = self._confidence_score(contexts)
        consistency_score = self._consistency_score(contexts)
        quality_score = round((confidence_score + consistency_score) / 2, 2)
        return ContextQualityResult(
            total_contexts=total_contexts,
            confidence_score=confidence_score,
            consistency_score=consistency_score,
            quality_score=quality_score,
        )

    def _confidence_score(self, contexts: tuple[MarketContext, ...]) -> float:
        total = 0.0
        for context in contexts:
            total += self._bounded_confidence(context.confidence)
        return round((total / len(contexts)) * 100, 2)

    def _consistency_score(self, contexts: tuple[MarketContext, ...]) -> float:
        consistent = 0
        for context in contexts:
            if self._is_consistent(context):
                consistent += 1
        return round((consistent / len(contexts)) * 100, 2)

    def _is_consistent(self, context: MarketContext) -> bool:
        return (
            bool(context.timestamp.strip())
            and bool(context.regime.strip())
            and bool(context.session.strip())
            and self._valid_number(context.volatility)
            and self._valid_number(context.liquidity)
            and isfinite(context.momentum)
            and 0.0 <= context.confidence <= 1.0
        )

    def _valid_number(self, value: float) -> bool:
        return isfinite(value) and value >= 0

    def _bounded_confidence(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value < 0:
            return 0.0
        if value > 1:
            return 1.0
        return value
