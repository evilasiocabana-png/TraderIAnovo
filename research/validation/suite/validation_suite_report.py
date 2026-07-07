"""Relatorio oficial da Validation Suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.validation.suite.validation_certification import (
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite_result import ValidationSuiteResult


@dataclass(frozen=True)
class ValidationSuiteReport:
    """Consolida informacoes produzidas pela Validation Suite."""

    validation_result: ValidationSuiteResult
    certification_result: ValidationCertificationResult
    scientific_score: float
    robustness_score: float
    reproducibility_score: float
    certification: str
    executed_validations: tuple[str, ...]
    execution_time: float
    metadata: Mapping[str, object]
