"""Engine de dominancia entre Alphas."""

from __future__ import annotations

from dataclasses import dataclass

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)


ALPHA_A_DOMINATES = "ALPHA_A_DOMINATES"
ALPHA_B_DOMINATES = "ALPHA_B_DOMINATES"
TIE = "TIE"


@dataclass(frozen=True)
class AlphaDominanceResult:
    """Resultado institucional de dominancia entre duas Alphas."""

    benchmark_id: str
    alpha_a: str
    alpha_b: str
    decision: str
    alpha_a_score: int
    alpha_b_score: int
    compared_metrics: tuple[str, ...]


@dataclass(frozen=True)
class AlphaDominanceEngine:
    """Determina dominancia usando apenas metricas comparadas."""

    def decide(
        self,
        benchmark_result: AlphaBenchmarkResult,
    ) -> AlphaDominanceResult:
        """Produz decisao de dominancia sem recalcular metricas."""
        alpha_a = self._comparison_for(
            benchmark_result,
            benchmark_result.profile.alpha_a,
        )
        alpha_b = self._comparison_for(
            benchmark_result,
            benchmark_result.profile.alpha_b,
        )
        if alpha_a is None or alpha_b is None:
            return self._result(benchmark_result, 0, 0)

        alpha_a_score = 0
        alpha_b_score = 0
        for metric in benchmark_result.profile.metrics:
            winner = self._winner(metric, alpha_a, alpha_b)
            if winner == benchmark_result.profile.alpha_a:
                alpha_a_score += 1
            if winner == benchmark_result.profile.alpha_b:
                alpha_b_score += 1

        return self._result(benchmark_result, alpha_a_score, alpha_b_score)

    def _comparison_for(
        self,
        benchmark_result: AlphaBenchmarkResult,
        alpha_id: str,
    ) -> AlphaBenchmarkComparison | None:
        for comparison in benchmark_result.comparisons:
            if comparison.alpha_id == alpha_id:
                return comparison
        return None

    def _winner(
        self,
        metric: str,
        alpha_a: AlphaBenchmarkComparison,
        alpha_b: AlphaBenchmarkComparison,
    ) -> str | None:
        normalized = metric.strip().casefold()
        if normalized == "max_drawdown":
            return self._lower_winner(alpha_a, alpha_b, "max_drawdown")
        return self._higher_winner(alpha_a, alpha_b, normalized)

    def _higher_winner(
        self,
        alpha_a: AlphaBenchmarkComparison,
        alpha_b: AlphaBenchmarkComparison,
        attribute: str,
    ) -> str | None:
        value_a = self._metric_value(alpha_a, attribute)
        value_b = self._metric_value(alpha_b, attribute)
        if value_a > value_b:
            return alpha_a.alpha_id
        if value_b > value_a:
            return alpha_b.alpha_id
        return None

    def _lower_winner(
        self,
        alpha_a: AlphaBenchmarkComparison,
        alpha_b: AlphaBenchmarkComparison,
        attribute: str,
    ) -> str | None:
        value_a = self._metric_value(alpha_a, attribute)
        value_b = self._metric_value(alpha_b, attribute)
        if value_a < value_b:
            return alpha_a.alpha_id
        if value_b < value_a:
            return alpha_b.alpha_id
        return None

    def _metric_value(
        self,
        comparison: AlphaBenchmarkComparison,
        attribute: str,
    ) -> float:
        value = getattr(comparison, attribute, 0.0)
        if not isinstance(value, (int, float)):
            return 0.0
        return float(value)

    def _result(
        self,
        benchmark_result: AlphaBenchmarkResult,
        alpha_a_score: int,
        alpha_b_score: int,
    ) -> AlphaDominanceResult:
        return AlphaDominanceResult(
            benchmark_id=benchmark_result.profile.benchmark_id,
            alpha_a=benchmark_result.profile.alpha_a,
            alpha_b=benchmark_result.profile.alpha_b,
            decision=self._decision(alpha_a_score, alpha_b_score),
            alpha_a_score=alpha_a_score,
            alpha_b_score=alpha_b_score,
            compared_metrics=benchmark_result.profile.metrics,
        )

    def _decision(
        self,
        alpha_a_score: int,
        alpha_b_score: int,
    ) -> str:
        if alpha_a_score > alpha_b_score:
            return ALPHA_A_DOMINATES
        if alpha_b_score > alpha_a_score:
            return ALPHA_B_DOMINATES
        return TIE
