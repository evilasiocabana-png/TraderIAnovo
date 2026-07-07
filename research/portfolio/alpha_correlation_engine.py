"""Motor de correlacao entre curvas de resultado de Alphas."""

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence


@dataclass(frozen=True)
class AlphaCorrelationResult:
    """Resultado da correlacao entre Alphas."""

    alpha_ids: tuple[str, ...]
    correlation_matrix: tuple[tuple[float, ...], ...]
    average_correlation: float
    highest_correlation: float
    lowest_correlation: float


@dataclass(frozen=True)
class AlphaCorrelationEngine:
    """Calcula correlacao de Pearson sem otimizar carteira."""

    def calculate(
        self,
        curves: Mapping[str, Sequence[float]],
    ) -> AlphaCorrelationResult:
        """Calcula matriz de correlacao para curvas ja produzidas."""
        alpha_ids = tuple(curves.keys())
        matrix = tuple(
            tuple(
                self._correlation(curves[left], curves[right])
                for right in alpha_ids
            )
            for left in alpha_ids
        )
        pair_correlations = tuple(
            matrix[left][right]
            for left in range(len(alpha_ids))
            for right in range(left + 1, len(alpha_ids))
        )
        return AlphaCorrelationResult(
            alpha_ids=alpha_ids,
            correlation_matrix=matrix,
            average_correlation=self._average(pair_correlations),
            highest_correlation=max(pair_correlations, default=0.0),
            lowest_correlation=min(pair_correlations, default=0.0),
        )

    def _correlation(
        self,
        left_values: Sequence[float],
        right_values: Sequence[float],
    ) -> float:
        left = tuple(float(value) for value in left_values)
        right = tuple(float(value) for value in right_values)
        size = min(len(left), len(right))
        if size == 0:
            return 0.0
        left = left[:size]
        right = right[:size]
        if left == right:
            return 1.0
        left_mean = self._average(left)
        right_mean = self._average(right)
        covariance = sum(
            (left[index] - left_mean) * (right[index] - right_mean)
            for index in range(size)
        )
        left_variance = sum((value - left_mean) ** 2 for value in left)
        right_variance = sum((value - right_mean) ** 2 for value in right)
        denominator = sqrt(left_variance * right_variance)
        if denominator == 0.0:
            return 0.0
        return float(covariance / denominator)

    def _average(self, values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))
