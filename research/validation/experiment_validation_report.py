"""Relatorio consolidado da validacao de experimentos."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.experiment_validation_runner import ValidationExecutionResult
from research.validation.validation_rule import ValidationRule


@dataclass(frozen=True)
class ExperimentValidationReport:
    """Consolida resultados produzidos pelo Validation Runner."""

    validation_result: ValidationExecutionResult
    rules: tuple[ValidationRule, ...]
    total_rules: int
    passed_rules: tuple[ValidationRule, ...]
    failed_rules: tuple[ValidationRule, ...]
    skipped_rules: tuple[ValidationRule, ...]
    validation_messages: tuple[str, ...]
    execution_time: float
