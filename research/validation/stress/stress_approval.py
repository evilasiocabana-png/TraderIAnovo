"""Gate oficial de aprovacao da validacao sob estresse."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.stress.stress_report import StressReport


APPROVED = "APPROVED"
WARNING = "WARNING"
FAILED = "FAILED"


@dataclass(frozen=True)
class StressApprovalResult:
    """Resultado institucional da aprovacao sob estresse."""

    status: str
    message: str
    report: StressReport


@dataclass(frozen=True)
class StressApproval:
    """Produz decisao institucional sem executar pesquisas."""

    minimum_resilience_score: float = 0.7
    minimum_stability_score: float = 0.7
    maximum_degradation_score: float = 0.3

    def evaluate(
        self,
        report: StressReport,
    ) -> StressApprovalResult:
        """Classifica o relatorio de estresse em aprovado, alerta ou falha."""
        if (
            report.resilience_score < self.minimum_resilience_score
            or report.stability_score < self.minimum_stability_score
            or report.degradation_score > self.maximum_degradation_score
        ):
            return StressApprovalResult(
                status=FAILED,
                message="Stress validation failed.",
                report=report,
            )
        if (
            report.resilience_score == self.minimum_resilience_score
            or report.stability_score == self.minimum_stability_score
            or report.degradation_score == self.maximum_degradation_score
        ):
            return StressApprovalResult(
                status=WARNING,
                message="Stress validation completed with warnings.",
                report=report,
            )
        return StressApprovalResult(
            status=APPROVED,
            message="Stress validation approved.",
            report=report,
        )
