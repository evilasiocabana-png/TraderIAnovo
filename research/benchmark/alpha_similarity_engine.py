"""Engine de similaridade entre Alphas."""

from __future__ import annotations

from dataclasses import dataclass

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)


@dataclass(frozen=True)
class AlphaSimilarityResult:
    """Scores de similaridade e diversificacao entre Alphas."""

    similarity_score: float
    overlap_score: float
    diversification_score: float


@dataclass(frozen=True)
class AlphaSimilarityEngine:
    """Mede similaridade usando apenas metricas ja comparadas."""

    def calculate(
        self,
        benchmark_result: AlphaBenchmarkResult,
    ) -> AlphaSimilarityResult:
        """Calcula scores de redundancia sem recalcular metricas de pesquisa."""
        alpha_a = self._comparison_for(
            benchmark_result,
            benchmark_result.profile.alpha_a,
        )
        alpha_b = self._comparison_for(
            benchmark_result,
            benchmark_result.profile.alpha_b,
        )
        if alpha_a is None or alpha_b is None:
            return AlphaSimilarityResult(0.0, 0.0, 1.0)

        similarities = tuple(
            self._metric_similarity(metric, alpha_a, alpha_b)
            for metric in benchmark_result.profile.metrics
        )
        if not similarities:
            return AlphaSimilarityResult(0.0, 0.0, 1.0)

        similarity_score = self._average(similarities)
        overlap_score = self._overlap_score(similarities)
        diversification_score = 1.0 - similarity_score
        return AlphaSimilarityResult(
            similarity_score=similarity_score,
            overlap_score=overlap_score,
            diversification_score=diversification_score,
        )

    def _comparison_for(
        self,
        benchmark_result: AlphaBenchmarkResult,
        alpha_id: str,
    ) -> AlphaBenchmarkComparison | None:
        for comparison in benchmark_result.comparisons:
            if comparison.alpha_id == alpha_id:
                return comparison
        return None

    def _metric_similarity(
        self,
        metric: str,
        alpha_a: AlphaBenchmarkComparison,
        alpha_b: AlphaBenchmarkComparison,
    ) -> float:
        value_a = self._metric_value(alpha_a, metric)
        value_b = self._metric_value(alpha_b, metric)
        denominator = max(abs(value_a), abs(value_b), 1.0)
        return self._clamp(1.0 - (abs(value_a - value_b) / denominator))

    def _metric_value(
        self,
        comparison: AlphaBenchmarkComparison,
        metric: str,
    ) -> float:
        value = getattr(comparison, metric.strip().casefold(), 0.0)
        if not isinstance(value, (int, float)):
            return 0.0
        return float(value)

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return self._clamp(sum(values) / len(values))

    def _overlap_score(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        overlapping = sum(1 for value in values if value >= 0.8)
        return self._clamp(overlapping / len(values))

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
