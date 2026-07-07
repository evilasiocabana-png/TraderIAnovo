"""Motor oficial de otimizacao de portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_profile import (
    PortfolioOptimizationProfile,
)


@dataclass(frozen=True)
class PortfolioOptimizationResult:
    """Resultado da otimizacao declarativa de portfolio."""

    profile_id: str
    optimization_goal: str
    allocation_method: str
    selected_weights: Mapping[str, float]
    equal_weight: Mapping[str, float]
    risk_adjusted_weight: Mapping[str, float]
    benchmark_recommendation: str
    execution_time: float
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class PortfolioOptimizationEngine:
    """Seleciona pesos permitidos sem otimizacao matematica avancada."""

    def optimize(
        self,
        profile: PortfolioOptimizationProfile,
        weights: AllocationWeightResult,
        benchmark_report: AlphaBenchmarkReport,
    ) -> PortfolioOptimizationResult:
        """Consolida a otimizacao usando pesos ja calculados."""
        selected_weights = self._selected_weights(profile, weights)
        return PortfolioOptimizationResult(
            profile_id=profile.profile_id,
            optimization_goal=profile.optimization_goal,
            allocation_method=profile.allocation_method,
            selected_weights=selected_weights,
            equal_weight=weights.equal_weight,
            risk_adjusted_weight=weights.risk_adjusted_weight,
            benchmark_recommendation=benchmark_report.recommendation,
            execution_time=benchmark_report.execution_time,
            metadata=profile.metadata,
        )

    def _selected_weights(
        self,
        profile: PortfolioOptimizationProfile,
        weights: AllocationWeightResult,
    ) -> Mapping[str, float]:
        method = profile.allocation_method.strip().upper()
        if method == "RISK_ADJUSTED":
            return weights.risk_adjusted_weight
        return weights.equal_weight
