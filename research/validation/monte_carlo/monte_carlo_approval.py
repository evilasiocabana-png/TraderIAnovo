"""Gate oficial de aprovacao Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.monte_carlo.monte_carlo_report import MonteCarloReport


APPROVED = "APPROVED"
WARNING = "WARNING"
FAILED = "FAILED"


@dataclass(frozen=True)
class MonteCarloApprovalResult:
    """Resultado institucional da aprovacao Monte Carlo."""

    status: str
    message: str
    report: MonteCarloReport


@dataclass(frozen=True)
class MonteCarloApproval:
    """Produz decisao institucional sem executar pesquisas."""

    minimum_robustness_score: float = 0.7
    minimum_average_return: float = 0.0
    maximum_expected_drawdown: float = 0.3

    def evaluate(
        self,
        report: MonteCarloReport,
    ) -> MonteCarloApprovalResult:
        """Classifica o relatorio Monte Carlo em aprovado, alerta ou falha."""
        if (
            report.robustness_score < self.minimum_robustness_score
            or report.average_return < self.minimum_average_return
            or report.expected_drawdown > self.maximum_expected_drawdown
        ):
            return MonteCarloApprovalResult(
                status=FAILED,
                message="Monte Carlo validation failed.",
                report=report,
            )
        if (
            report.robustness_score == self.minimum_robustness_score
            or report.average_return == self.minimum_average_return
            or report.expected_drawdown == self.maximum_expected_drawdown
        ):
            return MonteCarloApprovalResult(
                status=WARNING,
                message="Monte Carlo validation completed with warnings.",
                report=report,
            )
        return MonteCarloApprovalResult(
            status=APPROVED,
            message="Monte Carlo validation approved.",
            report=report,
        )
