"""Avaliacao de risco teorico da alocacao de Alphas."""

from __future__ import annotations

from dataclasses import dataclass

from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_research_report import PortfolioResearchReport


@dataclass(frozen=True)
class AllocationRiskResult:
    """Resultado da avaliacao de risco da alocacao."""

    portfolio_exposure: float
    concentration_score: float
    aggregate_drawdown: float
    aggregate_risk_score: float


@dataclass(frozen=True)
class AllocationRiskEngine:
    """Avalia risco agregado sem alterar pesos ou metricas das Alphas."""

    def calculate(
        self,
        weights: AllocationWeightResult,
        report: PortfolioResearchReport,
    ) -> AllocationRiskResult:
        """Calcula indicadores de risco usando pesos e metricas consolidadas."""
        allocation = dict(weights.risk_adjusted_weight)
        exposure = sum(allocation.values())
        concentration = max(allocation.values()) if allocation else 0.0
        drawdown = self._aggregate_drawdown(allocation, report)
        risk_score = exposure + concentration + drawdown

        return AllocationRiskResult(
            portfolio_exposure=exposure,
            concentration_score=concentration,
            aggregate_drawdown=drawdown,
            aggregate_risk_score=risk_score,
        )

    def _aggregate_drawdown(
        self,
        allocation: dict[str, float],
        report: PortfolioResearchReport,
    ) -> float:
        drawdowns = {
            comparison.alpha_id: comparison.max_drawdown
            for comparison in report.comparison_result.comparisons
        }
        return sum(
            weight * drawdowns.get(alpha_id, 0.0)
            for alpha_id, weight in allocation.items()
        )
