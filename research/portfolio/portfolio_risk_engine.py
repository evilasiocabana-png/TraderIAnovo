"""Avaliacao agregada de risco do portfolio otimizado."""

from __future__ import annotations

from dataclasses import dataclass

from research.portfolio.allocation_risk_engine import AllocationRiskResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)


@dataclass(frozen=True)
class PortfolioRiskResult:
    """Resultado de risco agregado do portfolio."""

    aggregate_risk: float
    aggregate_drawdown: float
    concentration_score: float
    diversification_score: float


@dataclass(frozen=True)
class PortfolioRiskEngine:
    """Avalia risco agregado sem recalcular risco individual das Alphas."""

    def evaluate(
        self,
        optimization_result: PortfolioOptimizationResult,
        allocation_risk: AllocationRiskResult,
    ) -> PortfolioRiskResult:
        """Consolida risco agregado a partir de resultados existentes."""
        return PortfolioRiskResult(
            aggregate_risk=allocation_risk.aggregate_risk_score,
            aggregate_drawdown=allocation_risk.aggregate_drawdown,
            concentration_score=allocation_risk.concentration_score,
            diversification_score=self._diversification_score(
                optimization_result,
            ),
        )

    def _diversification_score(
        self,
        optimization_result: PortfolioOptimizationResult,
    ) -> float:
        weights = tuple(optimization_result.selected_weights.values())
        if not weights:
            return 0.0
        concentration = max(weights)
        return max(0.0, min(1.0, 1.0 - concentration))
