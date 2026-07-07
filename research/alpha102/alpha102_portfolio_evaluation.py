"""Avaliacao institucional da Alpha102 dentro do portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.alpha102.alpha102_benchmark import Alpha102BenchmarkResult
from research.benchmark.alpha_dominance_engine import (
    ALPHA_A_DOMINATES,
    ALPHA_B_DOMINATES,
)
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)


CONTINUE_RESEARCH = "CONTINUE_RESEARCH"
REJECT_AS_REDUNDANT = "REJECT_AS_REDUNDANT"
REJECT_PORTFOLIO_IMPACT = "REJECT_PORTFOLIO_IMPACT"


@dataclass(frozen=True)
class Alpha102PortfolioEvaluationResult:
    """Decisao oficial da Alpha Factory para a Alpha102."""

    improves_portfolio: bool
    worsens_portfolio: bool
    is_redundant: bool
    should_continue: bool
    official_decision: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class Alpha102PortfolioEvaluation:
    """Avalia valor incremental da Alpha102 sem recalcular metricas."""

    minimum_allocation_weight: float = 0.01
    redundancy_similarity_threshold: float = 0.8

    def evaluate(
        self,
        allocation: AllocationWeightResult,
        optimization: PortfolioOptimizationResult,
        benchmark: Alpha102BenchmarkResult,
    ) -> Alpha102PortfolioEvaluationResult:
        """Retorna decisao institucional a partir de resultados existentes."""
        alpha_weight = self._alpha102_weight(allocation, optimization)
        wins = self._count_decisions(
            benchmark.dominance_summary,
            ALPHA_A_DOMINATES,
        )
        losses = self._count_decisions(
            benchmark.dominance_summary,
            ALPHA_B_DOMINATES,
        )
        is_redundant = self._is_redundant(benchmark)
        worsens_portfolio = losses > wins
        improves_portfolio = (
            alpha_weight >= self.minimum_allocation_weight
            and wins >= losses
            and not is_redundant
        )
        should_continue = improves_portfolio or (
            alpha_weight >= self.minimum_allocation_weight
            and not worsens_portfolio
            and not is_redundant
        )
        decision = self._official_decision(
            should_continue,
            is_redundant,
        )
        return Alpha102PortfolioEvaluationResult(
            improves_portfolio=improves_portfolio,
            worsens_portfolio=worsens_portfolio,
            is_redundant=is_redundant,
            should_continue=should_continue,
            official_decision=decision,
            metadata={
                "alpha_id": benchmark.alpha_id,
                "allocation_weight": alpha_weight,
                "dominance_wins": wins,
                "dominance_losses": losses,
                "portfolio_position": benchmark.portfolio_position,
                "optimization_goal": optimization.optimization_goal,
                "benchmark_recommendation": optimization.benchmark_recommendation,
            },
        )

    def _alpha102_weight(
        self,
        allocation: AllocationWeightResult,
        optimization: PortfolioOptimizationResult,
    ) -> float:
        selected = optimization.selected_weights.get("Alpha102")
        if isinstance(selected, (int, float)):
            return float(selected)
        risk_adjusted = allocation.risk_adjusted_weight.get("Alpha102")
        if isinstance(risk_adjusted, (int, float)):
            return float(risk_adjusted)
        equal_weight = allocation.equal_weight.get("Alpha102", 0.0)
        if isinstance(equal_weight, (int, float)):
            return float(equal_weight)
        return 0.0

    def _count_decisions(
        self,
        decisions: Mapping[str, str],
        expected: str,
    ) -> int:
        return sum(1 for decision in decisions.values() if decision == expected)

    def _is_redundant(
        self,
        benchmark: Alpha102BenchmarkResult,
    ) -> bool:
        similarities = tuple(benchmark.similarity_summary.values())
        if not similarities:
            return False
        return all(
            similarity >= self.redundancy_similarity_threshold
            for similarity in similarities
        )

    def _official_decision(
        self,
        should_continue: bool,
        is_redundant: bool,
    ) -> str:
        if should_continue:
            return CONTINUE_RESEARCH
        if is_redundant:
            return REJECT_AS_REDUNDANT
        return REJECT_PORTFOLIO_IMPACT
