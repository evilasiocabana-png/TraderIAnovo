"""Certificacao oficial do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.suite.validation_suite_result import ValidationSuiteResult


RESEARCH_ONLY = "RESEARCH_ONLY"
VALIDATED = "VALIDATED"
ROBUST = "ROBUST"
PORTFOLIO_READY = "PORTFOLIO_READY"


@dataclass(frozen=True)
class ValidationCertificationResult:
    """Resultado da certificacao cientifica da Alpha."""

    status: str
    message: str
    validation_result: ValidationSuiteResult


@dataclass(frozen=True)
class ValidationCertification:
    """Produz certificacao cientifica sem aprovar operacao real."""

    validated_threshold: float = 0.5
    robust_threshold: float = 0.75
    portfolio_ready_threshold: float = 0.95

    def certify(
        self,
        result: ValidationSuiteResult,
    ) -> ValidationCertificationResult:
        """Classifica a Alpha conforme os scores cientificos consolidados."""
        status = self._status(result)
        return ValidationCertificationResult(
            status=status,
            message=self._message(status),
            validation_result=result,
        )

    def _status(self, result: ValidationSuiteResult) -> str:
        if (
            result.scientific_score >= self.portfolio_ready_threshold
            and result.robustness_score >= self.portfolio_ready_threshold
            and result.reproducibility_score >= self.portfolio_ready_threshold
        ):
            return PORTFOLIO_READY
        if (
            result.scientific_score >= self.robust_threshold
            and result.robustness_score >= self.robust_threshold
        ):
            return ROBUST
        if result.scientific_score >= self.validated_threshold:
            return VALIDATED
        return RESEARCH_ONLY

    def _message(self, status: str) -> str:
        if status == PORTFOLIO_READY:
            return "Alpha certified for portfolio research."
        if status == ROBUST:
            return "Alpha certified as scientifically robust."
        if status == VALIDATED:
            return "Alpha validated for continued research."
        return "Alpha remains research-only."
