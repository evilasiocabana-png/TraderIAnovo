"""Engine de substituicao de Alphas no portfolio quantitativo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.benchmark.alpha_dominance_engine import ALPHA_A_DOMINATES
from research.portfolio.portfolio_candidate import PortfolioCandidate
from research.portfolio.portfolio_optimization_report import (
    PortfolioOptimizationReport,
)


REPLACE = "REPLACE"
KEEP = "KEEP"
WAIT = "WAIT"


@dataclass(frozen=True)
class PortfolioReplacementResult:
    """Resultado institucional de substituicao de Alpha."""

    candidate_id: str
    alpha_id: str
    decision: str
    dominance_approved: bool
    benchmark_approved: bool
    similarity_approved: bool
    risk_approved: bool
    reasons: tuple[str, ...]
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class PortfolioReplacementEngine:
    """Decide substituicao usando apenas resultados existentes."""

    minimum_portfolio_score: float = 0.75
    maximum_similarity_score: float = 0.8
    maximum_aggregate_risk: float = 1.0

    def evaluate(
        self,
        candidate: PortfolioCandidate,
        optimization_report: PortfolioOptimizationReport,
    ) -> PortfolioReplacementResult:
        """Produz REPLACE, KEEP ou WAIT sem alterar o portfolio."""
        dominance_approved = self._dominance_approved(candidate)
        benchmark_approved = self._benchmark_approved(candidate)
        similarity_approved = self._similarity_approved(candidate)
        risk_approved = self._risk_approved(optimization_report)
        reasons = self._reasons(
            dominance_approved=dominance_approved,
            benchmark_approved=benchmark_approved,
            similarity_approved=similarity_approved,
            risk_approved=risk_approved,
        )
        decision = self._decision(
            dominance_approved=dominance_approved,
            benchmark_approved=benchmark_approved,
            similarity_approved=similarity_approved,
            risk_approved=risk_approved,
        )
        return PortfolioReplacementResult(
            candidate_id=candidate.candidate_id,
            alpha_id=candidate.alpha_id,
            decision=decision,
            dominance_approved=dominance_approved,
            benchmark_approved=benchmark_approved,
            similarity_approved=similarity_approved,
            risk_approved=risk_approved,
            reasons=reasons,
            metadata={
                "portfolio_score": candidate.portfolio_score,
                "dominance_decision": self._dominance_decision(candidate),
                "similarity_score": self._similarity_score(candidate),
                "aggregate_risk": optimization_report.aggregate_risk,
                "aggregate_drawdown": optimization_report.aggregate_drawdown,
            },
        )

    def _dominance_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return self._dominance_decision(candidate) == ALPHA_A_DOMINATES

    def _benchmark_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return candidate.portfolio_score >= self.minimum_portfolio_score

    def _similarity_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return self._similarity_score(candidate) <= self.maximum_similarity_score

    def _risk_approved(
        self,
        optimization_report: PortfolioOptimizationReport,
    ) -> bool:
        return optimization_report.aggregate_risk <= self.maximum_aggregate_risk

    def _dominance_decision(
        self,
        candidate: PortfolioCandidate,
    ) -> str:
        value = candidate.metadata.get("dominance_decision", "")
        return str(value)

    def _similarity_score(
        self,
        candidate: PortfolioCandidate,
    ) -> float:
        value = candidate.metadata.get("similarity_score", 1.0)
        if isinstance(value, (int, float)):
            return float(value)
        return 1.0

    def _decision(
        self,
        dominance_approved: bool,
        benchmark_approved: bool,
        similarity_approved: bool,
        risk_approved: bool,
    ) -> str:
        approvals = (
            dominance_approved,
            benchmark_approved,
            similarity_approved,
            risk_approved,
        )
        if all(approvals):
            return REPLACE
        if not dominance_approved or not benchmark_approved:
            return KEEP
        return WAIT

    def _reasons(
        self,
        dominance_approved: bool,
        benchmark_approved: bool,
        similarity_approved: bool,
        risk_approved: bool,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if not dominance_approved:
            reasons.append("Candidate does not dominate the target Alpha.")
        if not benchmark_approved:
            reasons.append("Benchmark score is below replacement threshold.")
        if not similarity_approved:
            reasons.append("Candidate is too similar to replace with confidence.")
        if not risk_approved:
            reasons.append("Aggregate portfolio risk is above threshold.")
        if not reasons:
            reasons.append("Candidate satisfies replacement criteria.")
        return tuple(reasons)
