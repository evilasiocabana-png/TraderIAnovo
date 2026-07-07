"""Executor oficial de regras de validacao do Research Lab."""

from dataclasses import dataclass

from research.alpha001_research_validator import Alpha001ResearchValidator
from research.research_execution_result import ResearchExecutionResult
from research.validation.validation_rule import ValidationRule
from research.validation.validation_rule_registry import ValidationRuleRegistry


@dataclass(frozen=True)
class ValidationExecutionResult:
    """Resultado da execucao das regras de validacao registradas."""

    passed_rules: tuple[ValidationRule, ...]
    failed_rules: tuple[ValidationRule, ...]
    skipped_rules: tuple[ValidationRule, ...]


@dataclass(frozen=True)
class ExperimentValidationRunner:
    """Executa regras registradas sem recalcular metricas."""

    def run(
        self,
        execution_result: ResearchExecutionResult,
        registry: ValidationRuleRegistry,
    ) -> ValidationExecutionResult:
        """Classifica regras registradas em aprovadas, falhas e ignoradas."""
        rules = registry.list()
        self._run_existing_validator(execution_result, rules)

        passed: list[ValidationRule] = []
        failed: list[ValidationRule] = []
        skipped: list[ValidationRule] = []

        for rule in rules:
            if not rule.enabled:
                skipped.append(rule)
                continue
            result = self._evaluate_rule(rule, execution_result)
            if result is None:
                skipped.append(rule)
            elif result:
                passed.append(rule)
            else:
                failed.append(rule)

        return ValidationExecutionResult(
            passed_rules=tuple(passed),
            failed_rules=tuple(failed),
            skipped_rules=tuple(skipped),
        )

    def _run_existing_validator(
        self,
        execution_result: ResearchExecutionResult,
        rules: tuple[ValidationRule, ...],
    ) -> None:
        thresholds = {rule.rule_id: rule.threshold for rule in rules}
        validator = Alpha001ResearchValidator(
            minimum_trades=int(thresholds.get("minimum_trades", 0.0)),
            minimum_profit_factor=thresholds.get("minimum_profit_factor", 0.0),
            maximum_drawdown=thresholds.get("maximum_drawdown", 0.0),
            minimum_win_rate=thresholds.get("minimum_win_rate", 0.0),
        )
        validator.validate(execution_result.research_report)

    def _evaluate_rule(
        self,
        rule: ValidationRule,
        execution_result: ResearchExecutionResult,
    ) -> bool | None:
        if rule.rule_id == "minimum_trades":
            return execution_result.metrics.total_trades >= rule.threshold
        if rule.rule_id == "maximum_drawdown":
            return execution_result.drawdown.max_drawdown_points <= rule.threshold
        if rule.rule_id == "minimum_profit_factor":
            return execution_result.profit_factor.profit_factor >= rule.threshold
        if rule.rule_id == "minimum_win_rate":
            return execution_result.win_rate.win_rate >= rule.threshold
        return None
