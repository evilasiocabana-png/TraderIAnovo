"""Gate institucional de validacao do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.experiment_validation_report import ExperimentValidationReport


@dataclass(frozen=True)
class ValidationGateResult:
    """Resultado da decisao institucional de validacao."""

    status: str
    message: str
    report: ExperimentValidationReport


@dataclass(frozen=True)
class ValidationGate:
    """Produz a decisao final a partir do relatorio de validacao."""

    def evaluate(
        self,
        report: ExperimentValidationReport,
    ) -> ValidationGateResult:
        """Classifica a validacao em PASSED, WARNING, FAILED ou BLOCKED."""
        if report.total_rules == 0:
            return ValidationGateResult(
                status="BLOCKED",
                message="Validation blocked: no rules available.",
                report=report,
            )
        if report.failed_rules:
            return ValidationGateResult(
                status="FAILED",
                message="Validation failed: at least one rule failed.",
                report=report,
            )
        if report.skipped_rules or report.validation_messages:
            return ValidationGateResult(
                status="WARNING",
                message="Validation completed with warnings.",
                report=report,
            )
        return ValidationGateResult(
            status="PASSED",
            message="Validation passed.",
            report=report,
        )
