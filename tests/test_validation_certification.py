"""Testes da certificacao oficial do Research Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.suite.validation_certification import (
    PORTFOLIO_READY,
    RESEARCH_ONLY,
    ROBUST,
    VALIDATED,
    ValidationCertification,
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.walk_forward_approval import WalkForwardApprovalResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationCertificationTest(unittest.TestCase):
    """Valida certificacao cientifica sem aprovacao operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationCertificationResult))
        self.assertTrue(ValidationCertificationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ValidationCertificationResult)],
            ["status", "message", "validation_result"],
        )

    def test_certification_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationCertification))
        self.assertTrue(ValidationCertification.__dataclass_params__.frozen)

    def test_certifica_research_only_para_score_baixo(self) -> None:
        result = ValidationCertification().certify(
            self._validation_result(
                scientific_score=0.4,
                robustness_score=0.4,
                reproducibility_score=0.4,
            )
        )

        self.assertEqual(result.status, RESEARCH_ONLY)
        self.assertEqual(result.message, "Alpha remains research-only.")

    def test_certifica_validated_para_score_cientifico_intermediario(self) -> None:
        validation_result = self._validation_result(
            scientific_score=0.6,
            robustness_score=0.4,
            reproducibility_score=0.4,
        )

        result = ValidationCertification().certify(validation_result)

        self.assertEqual(result.status, VALIDATED)
        self.assertIs(result.validation_result, validation_result)

    def test_certifica_robust_para_scores_altos_sem_portfolio_ready(self) -> None:
        result = ValidationCertification().certify(
            self._validation_result(
                scientific_score=0.8,
                robustness_score=0.8,
                reproducibility_score=0.5,
            )
        )

        self.assertEqual(result.status, ROBUST)

    def test_certifica_portfolio_ready_para_todos_scores_excelentes(self) -> None:
        result = ValidationCertification().certify(
            self._validation_result(
                scientific_score=1.0,
                robustness_score=1.0,
                reproducibility_score=1.0,
            )
        )

        self.assertEqual(result.status, PORTFOLIO_READY)

    def test_result_e_imutavel(self) -> None:
        result = ValidationCertification().certify(
            self._validation_result(
                scientific_score=1.0,
                robustness_score=1.0,
                reproducibility_score=1.0,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.status = RESEARCH_ONLY

    def test_certification_nao_aprova_operacao_real_ou_acessa_infra(self) -> None:
        source = read_source(
            Path("research/validation/suite/validation_certification.py")
        )
        forbidden_fragments = (
            "Broker",
            "Dashboard",
            "streamlit",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "BUY",
            "SELL",
            "COMPRA",
            "VENDA",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "ValidationGate",
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

    def test_certification_permanece_desacoplada_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/suite/validation_certification.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
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

    def _validation_result(
        self,
        scientific_score: float,
        robustness_score: float,
        reproducibility_score: float,
    ) -> ValidationSuiteResult:
        return ValidationSuiteResult(
            walk_forward_approval=self._walk_forward_approval(),
            monte_carlo_approval=self._monte_carlo_approval(),
            stress_approval=self._stress_approval(),
            scientific_score=scientific_score,
            robustness_score=robustness_score,
            reproducibility_score=reproducibility_score,
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
