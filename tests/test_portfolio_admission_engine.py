"""Testes do engine de admissao no portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.portfolio.portfolio_admission_engine import (
    ADMIT,
    HOLD,
    REJECT,
    PortfolioAdmissionEngine,
    PortfolioAdmissionResult,
)
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


class PortfolioAdmissionEngineTest(unittest.TestCase):
    """Valida admissao institucional de candidatas ao portfolio."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioAdmissionResult))
        self.assertTrue(PortfolioAdmissionResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioAdmissionResult)],
            [
                "candidate_id",
                "alpha_id",
                "decision",
                "benchmark_approved",
                "certification_approved",
                "diversification_approved",
                "robustness_approved",
                "reasons",
                "metadata",
            ],
        )

    def test_engine_admite_candidata_com_criterios_aprovados(self) -> None:
        result = PortfolioAdmissionEngine().evaluate(
            self._candidate(
                portfolio_score=0.85,
                certification="PORTFOLIO_READY",
                diversification=0.6,
                robustness=0.8,
            )
        )

        self.assertEqual(result.decision, ADMIT)
        self.assertTrue(result.benchmark_approved)
        self.assertTrue(result.certification_approved)
        self.assertTrue(result.diversification_approved)
        self.assertTrue(result.robustness_approved)
        self.assertEqual(
            result.reasons,
            ("Candidate satisfies portfolio admission criteria.",),
        )

    def test_engine_segura_candidata_com_certificacao_valida_e_gap_parcial(self) -> None:
        result = PortfolioAdmissionEngine().evaluate(
            self._candidate(
                portfolio_score=0.65,
                certification="VALIDATED",
                diversification=0.5,
                robustness=0.75,
            )
        )

        self.assertEqual(result.decision, HOLD)
        self.assertFalse(result.benchmark_approved)
        self.assertTrue(result.certification_approved)
        self.assertIn("Benchmark below admission threshold.", result.reasons)

    def test_engine_rejeita_candidata_sem_certificacao_suficiente(self) -> None:
        result = PortfolioAdmissionEngine().evaluate(
            self._candidate(
                portfolio_score=0.9,
                certification="RESEARCH_ONLY",
                diversification=0.7,
                robustness=0.8,
            )
        )

        self.assertEqual(result.decision, REJECT)
        self.assertFalse(result.certification_approved)
        self.assertIn("Validation certification is insufficient.", result.reasons)

    def test_engine_rejeita_candidata_sem_diversificacao_ou_robustez(self) -> None:
        result = PortfolioAdmissionEngine().evaluate(
            self._candidate(
                portfolio_score=0.9,
                certification="ROBUST",
                diversification=0.2,
                robustness=0.4,
            )
        )

        self.assertEqual(result.decision, HOLD)
        self.assertFalse(result.diversification_approved)
        self.assertFalse(result.robustness_approved)
        self.assertIn("Diversification score is insufficient.", result.reasons)
        self.assertIn("Robustness score is insufficient.", result.reasons)

    def test_engine_usa_robustez_do_benchmark_quando_metadata_nao_informa(self) -> None:
        candidate = self._candidate(
            portfolio_score=0.8,
            certification="ROBUST",
            diversification=0.5,
            robustness=None,
        )

        result = PortfolioAdmissionEngine().evaluate(candidate)

        self.assertEqual(result.metadata["robustness_score"], 0.82)
        self.assertTrue(result.robustness_approved)

    def test_result_e_imutavel(self) -> None:
        result = PortfolioAdmissionEngine().evaluate(
            self._candidate(
                portfolio_score=0.85,
                certification="PORTFOLIO_READY",
                diversification=0.6,
                robustness=0.8,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.decision = REJECT

    def test_engine_nao_altera_allocation_optimization_ou_executa_pesquisas(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_admission_engine.py"))
        forbidden_fragments = (
            "Allocation",
            "PortfolioOptimization",
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
            ".optimize(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".certify(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_admission_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "research.research_pipeline",
            "research.research_runner",
            "research.portfolio.allocation_weight_engine",
            "research.portfolio.portfolio_optimization_engine",
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
            "optimize",
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
        self.assertIn("research.portfolio.portfolio_candidate", imports)

    def _candidate(
        self,
        portfolio_score: float,
        certification: str,
        diversification: float,
        robustness: float | None,
    ) -> PortfolioCandidate:
        metadata = {"diversification_score": diversification}
        if robustness is not None:
            metadata["robustness_score"] = robustness
        return PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=self._benchmark_result(),
            validation_certification=self._certification(certification),
            portfolio_score=portfolio_score,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T14:30:00-03:00",
            metadata=metadata,
        )

    def _benchmark_result(self) -> AlphaBenchmarkResult:
        comparison = AlphaBenchmarkComparison(
            alpha_id="Alpha102",
            experiment_id="exp-alpha102",
            net_profit=100.0,
            max_drawdown=5.0,
            profit_factor=1.8,
            win_rate=0.6,
            expectancy=2.5,
            robustness=0.82,
            reproducibility=0.9,
        )
        return AlphaBenchmarkResult(
            profile=AlphaBenchmarkProfile(
                benchmark_id="benchmark-alpha102-alpha101",
                alpha_a="Alpha102",
                alpha_b="Alpha101",
                experiment_ids=("exp-alpha102", "exp-alpha101"),
                campaign_ids=("campaign-alpha102", "campaign-alpha101"),
                comparison_period="2026-Q1",
                metrics=("net_profit", "max_drawdown"),
                created_at="2026-06-28T14:30:00-03:00",
                metadata={},
            ),
            total_results=1,
            comparisons=(comparison,),
            best_net_profit=comparison,
            best_max_drawdown=comparison,
            best_profit_factor=comparison,
            best_win_rate=comparison,
            best_expectancy=comparison,
            best_robustness=comparison,
            best_reproducibility=comparison,
        )

    def _certification(self, status: str) -> ValidationCertificationResult:
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
            status=status,
            message=f"Certification status: {status}.",
            validation_result=validation_result,
        )


if __name__ == "__main__":
    unittest.main()
