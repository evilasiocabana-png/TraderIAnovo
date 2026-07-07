"""Calculo teorico de pesos de alocacao de Alphas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.portfolio.allocation_profile import AllocationProfile
from research.portfolio.portfolio_research_report import PortfolioResearchReport


@dataclass(frozen=True)
class AllocationWeightResult:
    """Resultado dos pesos teoricos de alocacao."""

    equal_weight: Mapping[str, float]
    risk_adjusted_weight: Mapping[str, float]


@dataclass(frozen=True)
class AllocationWeightEngine:
    """Calcula pesos teoricos sem otimizacao matematica avancada."""

    def calculate(
        self,
        profile: AllocationProfile,
        report: PortfolioResearchReport,
    ) -> AllocationWeightResult:
        """Retorna pesos equal weight e ajustados por risco."""
        alpha_ids = self._alpha_ids(profile, report)
        equal_weight = self._equal_weight(profile, alpha_ids)
        risk_adjusted_weight = self._risk_adjusted_weight(
            profile,
            report,
            alpha_ids,
            equal_weight,
        )
        return AllocationWeightResult(
            equal_weight=equal_weight,
            risk_adjusted_weight=risk_adjusted_weight,
        )

    def _alpha_ids(
        self,
        profile: AllocationProfile,
        report: PortfolioResearchReport,
    ) -> tuple[str, ...]:
        reported = tuple(
            comparison.alpha_id
            for comparison in report.comparison_result.comparisons
            if comparison.alpha_id in profile.alpha_ids
        )
        return reported or profile.alpha_ids

    def _equal_weight(
        self,
        profile: AllocationProfile,
        alpha_ids: tuple[str, ...],
    ) -> Mapping[str, float]:
        if not alpha_ids:
            return {}
        raw_weight = profile.max_total_exposure / len(alpha_ids)
        weight = min(raw_weight, profile.max_allocation_per_alpha)
        return {alpha_id: weight for alpha_id in alpha_ids}

    def _risk_adjusted_weight(
        self,
        profile: AllocationProfile,
        report: PortfolioResearchReport,
        alpha_ids: tuple[str, ...],
        fallback: Mapping[str, float],
    ) -> Mapping[str, float]:
        scores = {
            comparison.alpha_id: self._score(comparison.profit_factor, comparison.max_drawdown)
            for comparison in report.comparison_result.comparisons
            if comparison.alpha_id in alpha_ids
        }
        total_score = sum(scores.values())
        if total_score <= 0.0:
            return fallback
        return {
            alpha_id: min(
                profile.max_total_exposure * (scores.get(alpha_id, 0.0) / total_score),
                profile.max_allocation_per_alpha,
            )
            for alpha_id in alpha_ids
        }

    def _score(
        self,
        profit_factor: float,
        max_drawdown: float,
    ) -> float:
        safe_profit_factor = max(profit_factor, 0.0)
        safe_drawdown = max(max_drawdown, 0.0)
        return safe_profit_factor / (1.0 + safe_drawdown)
