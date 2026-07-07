"""Gate institucional de reprodutibilidade do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass

from research.reproducibility.reproducibility_report import ReproducibilityReport


@dataclass(frozen=True)
class ReproducibilityGateResult:
    """Resultado da decisao institucional de reprodutibilidade."""

    status: str
    message: str
    report: ReproducibilityReport


@dataclass(frozen=True)
class ReproducibilityGate:
    """Produz a decisao final a partir do relatorio de reprodutibilidade."""

    def evaluate(
        self,
        report: ReproducibilityReport,
    ) -> ReproducibilityGateResult:
        """Classifica a pesquisa como reprodutivel, parcial ou nao reprodutivel."""
        if report.validation_result.is_reproducible:
            return ReproducibilityGateResult(
                status="REPRODUCIBLE",
                message="Research execution is reproducible.",
                report=report,
            )
        if self._has_partial_compatibility(report):
            return ReproducibilityGateResult(
                status="PARTIALLY_REPRODUCIBLE",
                message="Research execution is partially reproducible.",
                report=report,
            )
        return ReproducibilityGateResult(
            status="NOT_REPRODUCIBLE",
            message="Research execution is not reproducible.",
            report=report,
        )

    def _has_partial_compatibility(
        self,
        report: ReproducibilityReport,
    ) -> bool:
        return (
            report.reproducibility_score > 0.0
            or report.compatible_versions
            or report.configuration_status == "COMPATIBLE"
            or report.dataset_status == "COMPATIBLE"
            or report.replay_status == "COMPATIBLE"
        )
