"""Gate oficial de aprovacao Walk-Forward."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.walk_forward_report import WalkForwardReport


APPROVED = "APPROVED"
WARNING = "WARNING"
FAILED = "FAILED"


@dataclass(frozen=True)
class WalkForwardApprovalResult:
    """Resultado institucional da aprovacao Walk-Forward."""

    status: str
    message: str
    report: WalkForwardReport


@dataclass(frozen=True)
class WalkForwardApproval:
    """Produz decisao institucional sem executar pesquisas."""

    minimum_stability: float = 0.7
    minimum_consistency: float = 0.7
    maximum_degradation: float = 0.3

    def evaluate(
        self,
        report: WalkForwardReport,
    ) -> WalkForwardApprovalResult:
        """Classifica o relatorio Walk-Forward em aprovado, alerta ou falha."""
        if (
            report.stability_score < self.minimum_stability
            or report.consistency_score < self.minimum_consistency
            or report.degradation_score > self.maximum_degradation
        ):
            return WalkForwardApprovalResult(
                status=FAILED,
                message="Walk-Forward validation failed.",
                report=report,
            )
        if (
            report.stability_score == self.minimum_stability
            or report.consistency_score == self.minimum_consistency
            or report.degradation_score == self.maximum_degradation
        ):
            return WalkForwardApprovalResult(
                status=WARNING,
                message="Walk-Forward validation completed with warnings.",
                report=report,
            )
        return WalkForwardApprovalResult(
            status=APPROVED,
            message="Walk-Forward validation approved.",
            report=report,
        )
