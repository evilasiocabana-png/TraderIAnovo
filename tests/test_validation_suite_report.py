"""Testes do relatorio oficial da Validation Suite."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.suite.validation_certification import (
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite_report import ValidationSuiteReport
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.walk_forward_approval import WalkForwardApprovalResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationSuiteReportTest(unittest.TestCase):
    """Valida relatorio puro da Validation Suite."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationSuiteReport))
        self.assertTrue(ValidationSuiteReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ValidationSuiteReport)],
            [
                "validation_result",
                "certification_result",
                "scientific_score",
                "robustness_score",
                "reproducibility_score",
                "certification",
                "executed_validations",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = ValidationSuiteReport.__annotations__

        self.assertEqual(annotations["validation_result"], "ValidationSuiteResult")
        self.assertEqual(
            annotations["certification_result"],
            "ValidationCertificationResult",
        )
        self.assertEqual(annotations["scientific_score"], "float")
        self.assertEqual(annotations["robustness_score"], "float")
        self.assertEqual(annotations["reproducibility_score"], "float")
        self.assertEqual(annotations["certification"], "str")
        self.assertEqual(annotations["executed_validations"], "tuple[str, ...]")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_resultados_anteriores(self) -> None:
        validation_result = self._validation_result()
        certification_result = self._certification_result(validation_result)

        report = ValidationSuiteReport(
            validation_result=validation_result,
            certification_result=certification_result,
            scientific_score=validation_result.scientific_score,
            robustness_score=validation_result.robustness_score,
            reproducibility_score=validation_result.reproducibility_score,
            certification=certification_result.status,
            executed_validations=(
                "WALK_FORWARD",
                "MONTE_CARLO",
                "STRESS_TESTING",
            ),
            execution_time=3.5,
            metadata={"source": "unit-test"},
        )

        self.assertIs(report.validation_result, validation_result)
        self.assertIs(report.certification_result, certification_result)
        self.assertEqual(report.scientific_score, 1.0)
        self.assertEqual(report.robustness_score, 0.9)
        self.assertEqual(report.reproducibility_score, 0.8)
        self.assertEqual(report.certification, "ROBUST")
        self.assertEqual(
            report.executed_validations,
            ("WALK_FORWARD", "MONTE_CARLO", "STRESS_TESTING"),
        )
        self.assertEqual(report.execution_time, 3.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_e_imutavel(self) -> None:
        validation_result = self._validation_result()
        report = ValidationSuiteReport(
            validation_result=validation_result,
            certification_result=self._certification_result(validation_result),
            scientific_score=1.0,
            robustness_score=0.9,
            reproducibility_score=0.8,
            certification="ROBUST",
            executed_validations=("WALK_FORWARD",),
            execution_time=3.5,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.certification = "VALIDATED"

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(
            Path("research/validation/suite/validation_suite_report.py")
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
            ".run(",
            ".calculate(",
            ".analyze(",
            ".validate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/validation/suite/validation_suite_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "research.validation.validation_gate",
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
            "calculate",
            "analyze",
            "validate",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _validation_result(self) -> ValidationSuiteResult:
        return ValidationSuiteResult(
            walk_forward_approval=self._walk_forward_approval(),
            monte_carlo_approval=self._monte_carlo_approval(),
            stress_approval=self._stress_approval(),
            scientific_score=1.0,
            robustness_score=0.9,
            reproducibility_score=0.8,
        )

    def _certification_result(
        self,
        validation_result: ValidationSuiteResult,
    ) -> ValidationCertificationResult:
        return ValidationCertificationResult(
            status="ROBUST",
            message="Alpha certified as scientifically robust.",
            validation_result=validation_result,
        )

    def _walk_forward_approval(self) -> WalkForwardApprovalResult:
        return WalkForwardApprovalResult(
            status="APPROVED",
            message="Walk Forward approved.",
            report=None,
        )

    def _monte_carlo_approval(self) -> MonteCarloApprovalResult:
        return MonteCarloApprovalResult(
            status="APPROVED",
            message="Monte Carlo approved.",
            report=None,
        )

    def _stress_approval(self) -> StressApprovalResult:
        return StressApprovalResult(
            status="APPROVED",
            message="Stress approved.",
            report=None,
        )


if __name__ == "__main__":
    unittest.main()
