"""Testes do relatorio oficial de evolucao do portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.portfolio.portfolio_admission_engine import PortfolioAdmissionResult
from research.portfolio.portfolio_candidate import PortfolioCandidate
from research.portfolio.portfolio_evolution_report import PortfolioEvolutionReport
from research.portfolio.portfolio_replacement_engine import (
    PortfolioReplacementResult,
)
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


class PortfolioEvolutionReportTest(unittest.TestCase):
    """Valida relatorio puro de evolucao do portfolio."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioEvolutionReport))
        self.assertTrue(PortfolioEvolutionReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioEvolutionReport)],
            [
                "candidates",
                "admission_results",
                "replacement_results",
                "total_candidates",
                "admitted",
                "rejected",
                "replaced",
                "waiting",
                "diversification_score",
                "portfolio_health",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = PortfolioEvolutionReport.__annotations__

        self.assertEqual(annotations["candidates"], "tuple[PortfolioCandidate, ...]")
        self.assertEqual(
            annotations["admission_results"],
            "tuple[PortfolioAdmissionResult, ...]",
        )
        self.assertEqual(
            annotations["replacement_results"],
            "tuple[PortfolioReplacementResult, ...]",
        )
        self.assertEqual(annotations["total_candidates"], "int")
        self.assertEqual(annotations["admitted"], "int")
        self.assertEqual(annotations["rejected"], "int")
        self.assertEqual(annotations["replaced"], "int")
        self.assertEqual(annotations["waiting"], "int")
        self.assertEqual(annotations["diversification_score"], "float")
        self.assertEqual(annotations["portfolio_health"], "str")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_consolida_resultados_anteriores(self) -> None:
        candidate = self._candidate()
        admission = self._admission()
        replacement = self._replacement()

        report = PortfolioEvolutionReport(
            candidates=(candidate,),
            admission_results=(admission,),
            replacement_results=(replacement,),
            total_candidates=1,
            admitted=1,
            rejected=0,
            replaced=1,
            waiting=0,
            diversification_score=0.72,
            portfolio_health="HEALTHY",
            execution_time=2.5,
            metadata={"source": "unit-test"},
        )

        self.assertEqual(report.candidates, (candidate,))
        self.assertEqual(report.admission_results, (admission,))
        self.assertEqual(report.replacement_results, (replacement,))
        self.assertEqual(report.total_candidates, 1)
        self.assertEqual(report.admitted, 1)
        self.assertEqual(report.rejected, 0)
        self.assertEqual(report.replaced, 1)
        self.assertEqual(report.waiting, 0)
        self.assertEqual(report.diversification_score, 0.72)
        self.assertEqual(report.portfolio_health, "HEALTHY")
        self.assertEqual(report.execution_time, 2.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        candidates = (self._candidate(),)
        admissions = (self._admission(),)
        replacements = (self._replacement(),)
        metadata = {"source": "unit-test"}

        report = PortfolioEvolutionReport(
            candidates=candidates,
            admission_results=admissions,
            replacement_results=replacements,
            total_candidates=1,
            admitted=1,
            rejected=0,
            replaced=1,
            waiting=0,
            diversification_score=0.72,
            portfolio_health="HEALTHY",
            execution_time=2.5,
            metadata=metadata,
        )

        self.assertIs(report.candidates, candidates)
        self.assertIs(report.admission_results, admissions)
        self.assertIs(report.replacement_results, replacements)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = PortfolioEvolutionReport(
            candidates=(self._candidate(),),
            admission_results=(self._admission(),),
            replacement_results=(self._replacement(),),
            total_candidates=1,
            admitted=1,
            rejected=0,
            replaced=1,
            waiting=0,
            diversification_score=0.72,
            portfolio_health="HEALTHY",
            execution_time=2.5,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.portfolio_health = "WEAK"

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_evolution_report.py"))
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
            ".execute(",
            ".calculate(",
            ".evaluate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/portfolio_evolution_report.py")
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
            "calculate",
            "evaluate",
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.portfolio.portfolio_candidate", imports)
        self.assertIn("research.portfolio.portfolio_admission_engine", imports)
        self.assertIn("research.portfolio.portfolio_replacement_engine", imports)

    def _candidate(self) -> PortfolioCandidate:
        return PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=self._benchmark_result(),
            validation_certification=self._certification(),
            portfolio_score=0.84,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T15:00:00-03:00",
            metadata={},
        )

    def _admission(self) -> PortfolioAdmissionResult:
        return PortfolioAdmissionResult(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            decision="ADMIT",
            benchmark_approved=True,
            certification_approved=True,
            diversification_approved=True,
            robustness_approved=True,
            reasons=("Candidate satisfies portfolio admission criteria.",),
            metadata={},
        )

    def _replacement(self) -> PortfolioReplacementResult:
        return PortfolioReplacementResult(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            decision="REPLACE",
            dominance_approved=True,
            benchmark_approved=True,
            similarity_approved=True,
            risk_approved=True,
            reasons=("Candidate satisfies replacement criteria.",),
            metadata={},
        )

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
                created_at="2026-06-28T15:00:00-03:00",
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
