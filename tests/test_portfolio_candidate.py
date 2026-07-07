"""Testes do contrato oficial de candidata ao portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.portfolio.portfolio_candidate import PortfolioCandidate
from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.suite.validation_certification import (
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.walk_forward_approval import WalkForwardApprovalResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioCandidateTest(unittest.TestCase):
    """Valida contrato puro de candidata ao portfolio quantitativo."""

    def test_candidate_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioCandidate))
        self.assertTrue(PortfolioCandidate.__dataclass_params__.frozen)

    def test_candidate_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioCandidate)],
            [
                "candidate_id",
                "alpha_id",
                "benchmark_result",
                "validation_certification",
                "portfolio_score",
                "current_status",
                "created_at",
                "metadata",
            ],
        )

    def test_candidate_possui_type_hints_explicitos(self) -> None:
        annotations = PortfolioCandidate.__annotations__

        self.assertEqual(annotations["candidate_id"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["benchmark_result"], "AlphaBenchmarkResult")
        self.assertEqual(
            annotations["validation_certification"],
            "ValidationCertificationResult",
        )
        self.assertEqual(annotations["portfolio_score"], "float")
        self.assertEqual(annotations["current_status"], "str")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_candidate_representa_alpha_candidata_ao_portfolio(self) -> None:
        benchmark = self._benchmark_result()
        certification = self._certification()

        candidate = PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=benchmark,
            validation_certification=certification,
            portfolio_score=0.84,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T14:15:00-03:00",
            metadata={"source": "unit-test"},
        )

        self.assertEqual(candidate.candidate_id, "candidate-alpha102-001")
        self.assertEqual(candidate.alpha_id, "Alpha102")
        self.assertIs(candidate.benchmark_result, benchmark)
        self.assertIs(candidate.validation_certification, certification)
        self.assertEqual(candidate.portfolio_score, 0.84)
        self.assertEqual(candidate.current_status, "PORTFOLIO_CANDIDATE")
        self.assertEqual(candidate.created_at, "2026-06-28T14:15:00-03:00")
        self.assertEqual(candidate.metadata["source"], "unit-test")

    def test_candidate_preserva_objetos_reutilizados(self) -> None:
        benchmark = self._benchmark_result()
        certification = self._certification()
        metadata = {"alpha_family": "SWING"}

        candidate = PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=benchmark,
            validation_certification=certification,
            portfolio_score=0.84,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T14:15:00-03:00",
            metadata=metadata,
        )

        self.assertIs(candidate.benchmark_result, benchmark)
        self.assertIs(candidate.validation_certification, certification)
        self.assertIs(candidate.metadata, metadata)

    def test_candidate_e_imutavel(self) -> None:
        candidate = PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=self._benchmark_result(),
            validation_certification=self._certification(),
            portfolio_score=0.84,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T14:15:00-03:00",
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            candidate.current_status = "APPROVED"

    def test_candidate_nao_altera_benchmark_alpha_ou_executa_pesquisas(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_candidate.py"))
        forbidden_fragments = (
            "def ",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".certify(",
            "benchmark_result =",
            "validation_certification =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_candidate_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/portfolio/portfolio_candidate.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
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
            "calculate",
            "compare",
            "validate",
            "certify",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.benchmark.alpha_benchmark_engine", imports)
        self.assertIn("research.validation.suite.validation_certification", imports)

    def _benchmark_result(self) -> AlphaBenchmarkResult:
        return AlphaBenchmarkResult(
            profile=AlphaBenchmarkProfile(
                benchmark_id="benchmark-alpha102-alpha101",
                alpha_a="Alpha102",
                alpha_b="Alpha101",
                experiment_ids=("exp-alpha102", "exp-alpha101"),
                campaign_ids=("campaign-alpha102", "campaign-alpha101"),
                comparison_period="2026-Q1",
                metrics=("net_profit", "max_drawdown"),
                created_at="2026-06-28T14:15:00-03:00",
                metadata={},
            ),
            total_results=0,
            comparisons=(),
            best_net_profit=None,
            best_max_drawdown=None,
            best_profit_factor=None,
            best_win_rate=None,
            best_expectancy=None,
            best_robustness=None,
            best_reproducibility=None,
        )

    def _certification(self) -> ValidationCertificationResult:
        validation_result = ValidationSuiteResult(
            walk_forward_approval=WalkForwardApprovalResult(
                status="APPROVED",
                message="Walk Forward approved.",
                report=None,
            ),
            monte_carlo_approval=MonteCarloApprovalResult(
                status="APPROVED",
                message="Monte Carlo approved.",
                report=None,
            ),
            stress_approval=StressApprovalResult(
                status="APPROVED",
                message="Stress approved.",
                report=None,
            ),
            scientific_score=1.0,
            robustness_score=1.0,
            reproducibility_score=1.0,
        )
        return ValidationCertificationResult(
            status="PORTFOLIO_READY",
            message="Alpha certified for portfolio research.",
            validation_result=validation_result,
        )


if __name__ == "__main__":
    unittest.main()
