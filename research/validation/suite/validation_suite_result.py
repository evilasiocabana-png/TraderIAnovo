"""Resultado consolidado da Validation Suite."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.walk_forward_approval import WalkForwardApprovalResult


APPROVED = "APPROVED"
WARNING = "WARNING"
FAILED = "FAILED"


@dataclass(frozen=True)
class ValidationSuiteResult:
    """Consolida aprovacoes cientificas da Validation Suite."""

    walk_forward_approval: WalkForwardApprovalResult
    monte_carlo_approval: MonteCarloApprovalResult
    stress_approval: StressApprovalResult
    scientific_score: float
    robustness_score: float
    reproducibility_score: float

    @classmethod
    def from_approvals(
        cls,
        walk_forward_approval: WalkForwardApprovalResult,
        monte_carlo_approval: MonteCarloApprovalResult,
        stress_approval: StressApprovalResult,
    ) -> ValidationSuiteResult:
        """Consolida os scores institucionais a partir dos gates."""
        walk_forward_score = cls._score(walk_forward_approval.status)
        monte_carlo_score = cls._score(monte_carlo_approval.status)
        stress_score = cls._score(stress_approval.status)
        scientific_score = cls._average(
            (
                walk_forward_score,
                monte_carlo_score,
                stress_score,
            )
        )
        robustness_score = cls._average((monte_carlo_score, stress_score))
        reproducibility_score = walk_forward_score
        return cls(
            walk_forward_approval=walk_forward_approval,
            monte_carlo_approval=monte_carlo_approval,
            stress_approval=stress_approval,
            scientific_score=scientific_score,
            robustness_score=robustness_score,
            reproducibility_score=reproducibility_score,
        )

    @staticmethod
    def _score(status: str) -> float:
        normalized_status = status.strip().upper()
        if normalized_status == APPROVED:
            return 1.0
        if normalized_status == WARNING:
            return 0.5
        if normalized_status == FAILED:
            return 0.0
        return 0.0

    @staticmethod
    def _average(values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)
