"""Testes do relatorio consolidado de validacao de experimentos."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.experiment_validation_report import ExperimentValidationReport
from research.validation.experiment_validation_runner import ValidationExecutionResult
from research.validation.validation_rule import ValidationRule
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentValidationReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou geracao de saida."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentValidationReport))
        self.assertTrue(ExperimentValidationReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ExperimentValidationReport)]

        self.assertEqual(
            field_names,
            [
                "validation_result",
                "rules",
                "total_rules",
                "passed_rules",
                "failed_rules",
                "skipped_rules",
                "validation_messages",
                "execution_time",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = ExperimentValidationReport.__annotations__

        self.assertEqual(annotations["validation_result"], "ValidationExecutionResult")
        self.assertEqual(annotations["rules"], "tuple[ValidationRule, ...]")
        self.assertEqual(annotations["total_rules"], "int")
        self.assertEqual(annotations["passed_rules"], "tuple[ValidationRule, ...]")
        self.assertEqual(annotations["failed_rules"], "tuple[ValidationRule, ...]")
        self.assertEqual(annotations["skipped_rules"], "tuple[ValidationRule, ...]")
        self.assertEqual(annotations["validation_messages"], "tuple[str, ...]")
        self.assertEqual(annotations["execution_time"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.validation_result, ValidationExecutionResult)
        self.assertIsInstance(report.rules[0], ValidationRule)
        self.assertEqual(report.total_rules, 3)
        self.assertEqual(tuple(rule.rule_id for rule in report.passed_rules), ("rule-pass",))
        self.assertEqual(tuple(rule.rule_id for rule in report.failed_rules), ("rule-fail",))
        self.assertEqual(tuple(rule.rule_id for rule in report.skipped_rules), ("rule-skip",))
        self.assertEqual(report.validation_messages, ("1 regra falhou.",))
        self.assertEqual(report.execution_time, 2.5)

    def test_report_preserva_referencias_recebidas(self) -> None:
        passed = self._rule("rule-pass")
        failed = self._rule("rule-fail")
        skipped = self._rule("rule-skip")
        result = ValidationExecutionResult((passed,), (failed,), (skipped,))
        rules = (passed, failed, skipped)

        report = ExperimentValidationReport(
            validation_result=result,
            rules=rules,
            total_rules=3,
            passed_rules=(passed,),
            failed_rules=(failed,),
            skipped_rules=(skipped,),
            validation_messages=("1 regra falhou.",),
            execution_time=2.5,
        )

        self.assertIs(report.validation_result, result)
        self.assertIs(report.rules, rules)
        self.assertIs(report.passed_rules[0], passed)
        self.assertIs(report.failed_rules[0], failed)
        self.assertIs(report.skipped_rules[0], skipped)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.total_rules = 0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(
            Path("research/validation/experiment_validation_report.py")
        )
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "ResearchRunner",
            "ResearchPipeline",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/validation/experiment_validation_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "alpha",
            "strategies",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> ExperimentValidationReport:
        passed = self._rule("rule-pass")
        failed = self._rule("rule-fail")
        skipped = self._rule("rule-skip")
        result = ValidationExecutionResult((passed,), (failed,), (skipped,))
        return ExperimentValidationReport(
            validation_result=result,
            rules=(passed, failed, skipped),
            total_rules=3,
            passed_rules=(passed,),
            failed_rules=(failed,),
            skipped_rules=(skipped,),
            validation_messages=("1 regra falhou.",),
            execution_time=2.5,
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
