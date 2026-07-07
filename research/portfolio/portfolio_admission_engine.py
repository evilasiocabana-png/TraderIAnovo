"""Engine de admissao de Alphas no portfolio quantitativo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.portfolio.portfolio_candidate import PortfolioCandidate


ADMIT = "ADMIT"
HOLD = "HOLD"
REJECT = "REJECT"

PORTFOLIO_READY = "PORTFOLIO_READY"
ROBUST = "ROBUST"
VALIDATED = "VALIDATED"


@dataclass(frozen=True)
class PortfolioAdmissionResult:
    """Resultado institucional da admissao no portfolio."""

    candidate_id: str
    alpha_id: str
    decision: str
    benchmark_approved: bool
    certification_approved: bool
    diversification_approved: bool
    robustness_approved: bool
    reasons: tuple[str, ...]
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class PortfolioAdmissionEngine:
    """Decide admissao usando apenas resultados existentes da candidata."""

    minimum_portfolio_score: float = 0.7
    minimum_diversification_score: float = 0.4
    minimum_robustness_score: float = 0.7

    def evaluate(
        self,
        candidate: PortfolioCandidate,
    ) -> PortfolioAdmissionResult:
        """Produz ADMIT, HOLD ou REJECT para a candidata informada."""
        benchmark_approved = self._benchmark_approved(candidate)
        certification_approved = self._certification_approved(candidate)
        diversification_approved = self._diversification_approved(candidate)
        robustness_approved = self._robustness_approved(candidate)
        reasons = self._reasons(
            benchmark_approved=benchmark_approved,
            certification_approved=certification_approved,
            diversification_approved=diversification_approved,
            robustness_approved=robustness_approved,
        )
        decision = self._decision(
            benchmark_approved=benchmark_approved,
            certification_approved=certification_approved,
            diversification_approved=diversification_approved,
            robustness_approved=robustness_approved,
        )
        return PortfolioAdmissionResult(
            candidate_id=candidate.candidate_id,
            alpha_id=candidate.alpha_id,
            decision=decision,
            benchmark_approved=benchmark_approved,
            certification_approved=certification_approved,
            diversification_approved=diversification_approved,
            robustness_approved=robustness_approved,
            reasons=reasons,
            metadata={
                "candidate_status": candidate.current_status,
                "portfolio_score": candidate.portfolio_score,
                "certification": candidate.validation_certification.status,
                "diversification_score": self._diversification_score(candidate),
                "robustness_score": self._robustness_score(candidate),
            },
        )

    def _benchmark_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return candidate.portfolio_score >= self.minimum_portfolio_score

    def _certification_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        status = candidate.validation_certification.status.strip().upper()
        return status in {PORTFOLIO_READY, ROBUST, VALIDATED}

    def _diversification_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return (
            self._diversification_score(candidate)
            >= self.minimum_diversification_score
        )

    def _robustness_approved(
        self,
        candidate: PortfolioCandidate,
    ) -> bool:
        return self._robustness_score(candidate) >= self.minimum_robustness_score

    def _diversification_score(
        self,
        candidate: PortfolioCandidate,
    ) -> float:
        value = candidate.metadata.get("diversification_score", 0.0)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def _robustness_score(
        self,
        candidate: PortfolioCandidate,
    ) -> float:
        value = candidate.metadata.get("robustness_score", None)
        if isinstance(value, (int, float)):
            return float(value)
        comparisons = candidate.benchmark_result.comparisons
        if not comparisons:
            return 0.0
        return max(comparison.robustness for comparison in comparisons)

    def _decision(
        self,
        benchmark_approved: bool,
        certification_approved: bool,
        diversification_approved: bool,
        robustness_approved: bool,
    ) -> str:
        approvals = (
            benchmark_approved,
            certification_approved,
            diversification_approved,
            robustness_approved,
        )
        if all(approvals):
            return ADMIT
        if certification_approved and any(approvals):
            return HOLD
        return REJECT

    def _reasons(
        self,
        benchmark_approved: bool,
        certification_approved: bool,
        diversification_approved: bool,
        robustness_approved: bool,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if not benchmark_approved:
            reasons.append("Benchmark below admission threshold.")
        if not certification_approved:
            reasons.append("Validation certification is insufficient.")
        if not diversification_approved:
            reasons.append("Diversification score is insufficient.")
        if not robustness_approved:
            reasons.append("Robustness score is insufficient.")
        if not reasons:
            reasons.append("Candidate satisfies portfolio admission criteria.")
        return tuple(reasons)
