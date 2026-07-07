"""Testes do gate institucional de validacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.experiment_validation_report import ExperimentValidationReport
from research.validation.experiment_validation_runner import ValidationExecutionResult
from research.validation.validation_gate import ValidationGate, ValidationGateResult
from research.validation.validation_rule import ValidationRule
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationGateTest(unittest.TestCase):
    """Valida a decisao institucional sem acoplamento operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationGateResult))
        self.assertTrue(ValidationGateResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ValidationGateResult)]

        self.assertEqual(field_names, ["status", "message", "report"])

    def test_gate_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationGate))
        self.assertTrue(ValidationGate.__dataclass_params__.frozen)

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = ValidationGateResult.__annotations__

        self.assertEqual(annotations["status"], "str")
        self.assertEqual(annotations["message"], "str")
        self.assertEqual(annotations["report"], "ExperimentValidationReport")

    def test_gate_retorna_passed_quando_todas_regras_passam(self) -> None:
        report = self._report(
            total_rules=1,
            passed_rules=(self._rule("rule-pass"),),
        )

        result = ValidationGate().evaluate(report)

        self.assertEqual(result.status, "PASSED")
        self.assertIs(result.report, report)

    def test_gate_retorna_warning_quando_existem_regras_ignoradas(self) -> None:
        report = self._report(
            total_rules=1,
            skipped_rules=(self._rule("rule-skip"),),
        )

        result = ValidationGate().evaluate(report)

        self.assertEqual(result.status, "WARNING")
        self.assertIs(result.report, report)

    def test_gate_retorna_warning_quando_existem_mensagens(self) -> None:
        report = self._report(
            total_rules=1,
            passed_rules=(self._rule("rule-pass"),),
            validation_messages=("Amostra limitada.",),
        )

        result = ValidationGate().evaluate(report)

        self.assertEqual(result.status, "WARNING")

    def test_gate_retorna_failed_quando_existem_regras_falhas(self) -> None:
        report = self._report(
            total_rules=1,
            failed_rules=(self._rule("rule-fail"),),
        )

        result = ValidationGate().evaluate(report)

        self.assertEqual(result.status, "FAILED")
        self.assertIs(result.report, report)

    def test_gate_retorna_blocked_quando_nao_existirem_regras(self) -> None:
        report = self._report(total_rules=0)

        result = ValidationGate().evaluate(report)

        self.assertEqual(result.status, "BLOCKED")
        self.assertIs(result.report, report)

    def test_result_e_imutavel(self) -> None:
        report = self._report(total_rules=0)
        result = ValidationGate().evaluate(report)

        with self.assertRaises(FrozenInstanceError):
            result.status = "PASSED"

    def test_gate_nao_aprova_operacao_real_ou_gera_saida(self) -> None:
        source = read_source(Path("research/validation/validation_gate.py"))
        forbidden_fragments = (
            "Broker",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "order_send",
            "execute_order",
            "BUY",
            "SELL",
            "COMPRA",
            "VENDA",
            "MT5",
            "MetaTrader5",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_gate_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/validation/validation_gate.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.alpha001_research_validator",
            "research.alpha001_research_advisor",
            "strategies",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(
        self,
        total_rules: int,
        passed_rules: tuple[ValidationRule, ...] = (),
        failed_rules: tuple[ValidationRule, ...] = (),
        skipped_rules: tuple[ValidationRule, ...] = (),
        validation_messages: tuple[str, ...] = (),
    ) -> ExperimentValidationReport:
        rules = passed_rules + failed_rules + skipped_rules
        validation_result = ValidationExecutionResult(
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            skipped_rules=skipped_rules,
        )
        return ExperimentValidationReport(
            validation_result=validation_result,
            rules=rules,
            total_rules=total_rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            skipped_rules=skipped_rules,
            validation_messages=validation_messages,
            execution_time=1.0,
        )

    def _rule(self, rule_id: str) -> ValidationRule:
        return ValidationRule(
            rule_id=rule_id,
            name=rule_id,
            description="Regra de teste.",
            severity="LOW",
            threshold=1.0,
            enabled=True,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
