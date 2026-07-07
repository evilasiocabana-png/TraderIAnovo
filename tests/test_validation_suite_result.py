"""Testes do resultado consolidado da Validation Suite."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.walk_forward_approval import WalkForwardApprovalResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationSuiteResultTest(unittest.TestCase):
    """Valida consolidacao cientifica sem executar validacoes."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationSuiteResult))
        self.assertTrue(ValidationSuiteResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ValidationSuiteResult)],
            [
                "walk_forward_approval",
                "monte_carlo_approval",
                "stress_approval",
                "scientific_score",
                "robustness_score",
                "reproducibility_score",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = ValidationSuiteResult.__annotations__

        self.assertEqual(
            annotations["walk_forward_approval"],
            "WalkForwardApprovalResult",
        )
        self.assertEqual(
            annotations["monte_carlo_approval"],
            "MonteCarloApprovalResult",
        )
        self.assertEqual(annotations["stress_approval"], "StressApprovalResult")
        self.assertEqual(annotations["scientific_score"], "float")
        self.assertEqual(annotations["robustness_score"], "float")
        self.assertEqual(annotations["reproducibility_score"], "float")

    def test_from_approvals_calcula_scores_aprovados(self) -> None:
        walk_forward = self._walk_forward_approval("APPROVED")
        monte_carlo = self._monte_carlo_approval("APPROVED")
        stress = self._stress_approval("APPROVED")

        result = ValidationSuiteResult.from_approvals(
            walk_forward,
            monte_carlo,
            stress,
        )

        self.assertIs(result.walk_forward_approval, walk_forward)
        self.assertIs(result.monte_carlo_approval, monte_carlo)
        self.assertIs(result.stress_approval, stress)
        self.assertEqual(result.scientific_score, 1.0)
        self.assertEqual(result.robustness_score, 1.0)
        self.assertEqual(result.reproducibility_score, 1.0)

    def test_from_approvals_calcula_scores_com_alerta_e_falha(self) -> None:
        result = ValidationSuiteResult.from_approvals(
            self._walk_forward_approval("WARNING"),
            self._monte_carlo_approval("APPROVED"),
            self._stress_approval("FAILED"),
        )

        self.assertEqual(result.scientific_score, 0.5)
        self.assertEqual(result.robustness_score, 0.5)
        self.assertEqual(result.reproducibility_score, 0.5)

    def test_status_desconhecido_recebe_score_zero(self) -> None:
        result = ValidationSuiteResult.from_approvals(
            self._walk_forward_approval("UNKNOWN"),
            self._monte_carlo_approval("APPROVED"),
            self._stress_approval("WARNING"),
        )

        self.assertEqual(result.scientific_score, 0.5)
        self.assertEqual(result.robustness_score, 0.75)
        self.assertEqual(result.reproducibility_score, 0.0)

    def test_result_e_imutavel(self) -> None:
        result = ValidationSuiteResult.from_approvals(
            self._walk_forward_approval("APPROVED"),
            self._monte_carlo_approval("APPROVED"),
            self._stress_approval("APPROVED"),
        )

        with self.assertRaises(FrozenInstanceError):
            result.scientific_score = 0.0

    def test_result_nao_executa_validacoes_ou_altera_gate(self) -> None:
        source = read_source(
            Path("research/validation/suite/validation_suite_result.py")
        )
        forbidden_fragments = (
            "ValidationGate",
            "ResearchPipeline",
            "ResearchRunner",
            "ValidationRunner",
            "ExperimentValidationRunner",
            "WalkForwardEngine",
            "MonteCarloEngine",
            "StressEngine",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".validate(",
            ".analyze(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_result_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/suite/validation_suite_result.py")
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
            "openai",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "validate",
            "analyze",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _walk_forward_approval(self, status: str) -> WalkForwardApprovalResult:
        return WalkForwardApprovalResult(
            status=status,
            message=f"Walk Forward {status}",
            report=None,
        )

    def _monte_carlo_approval(self, status: str) -> MonteCarloApprovalResult:
        return MonteCarloApprovalResult(
            status=status,
            message=f"Monte Carlo {status}",
            report=None,
        )

    def _stress_approval(self, status: str) -> StressApprovalResult:
        return StressApprovalResult(
            status=status,
            message=f"Stress {status}",
            report=None,
        )


if __name__ == "__main__":
    unittest.main()
