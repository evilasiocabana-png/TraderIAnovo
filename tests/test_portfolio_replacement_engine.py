"""Testes do engine de substituicao de Alphas no portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_dominance_engine import (
    ALPHA_A_DOMINATES,
    ALPHA_B_DOMINATES,
)
from research.portfolio.allocation_simulation import AllocationSimulationResult
from research.portfolio.portfolio_candidate import PortfolioCandidate
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.portfolio.portfolio_optimization_report import (
    PortfolioOptimizationReport,
)
from research.portfolio.portfolio_replacement_engine import (
    KEEP,
    REPLACE,
    WAIT,
    PortfolioReplacementEngine,
    PortfolioReplacementResult,
)
from research.portfolio.portfolio_risk_engine import PortfolioRiskResult
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


class PortfolioReplacementEngineTest(unittest.TestCase):
    """Valida decisao institucional de substituicao sem remocao automatica."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioReplacementResult))
        self.assertTrue(PortfolioReplacementResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioReplacementResult)],
            [
                "candidate_id",
                "alpha_id",
                "decision",
                "dominance_approved",
                "benchmark_approved",
                "similarity_approved",
                "risk_approved",
                "reasons",
                "metadata",
            ],
        )

    def test_engine_replace_quando_todos_criterios_aprovam(self) -> None:
        result = PortfolioReplacementEngine().evaluate(
            candidate=self._candidate(
                portfolio_score=0.85,
                dominance=ALPHA_A_DOMINATES,
                similarity=0.35,
            ),
            optimization_report=self._report(aggregate_risk=0.8),
        )

        self.assertEqual(result.decision, REPLACE)
        self.assertTrue(result.dominance_approved)
        self.assertTrue(result.benchmark_approved)
        self.assertTrue(result.similarity_approved)
        self.assertTrue(result.risk_approved)
        self.assertEqual(result.reasons, ("Candidate satisfies replacement criteria.",))

    def test_engine_keep_quando_candidata_nao_domina(self) -> None:
        result = PortfolioReplacementEngine().evaluate(
            candidate=self._candidate(
                portfolio_score=0.9,
                dominance=ALPHA_B_DOMINATES,
                similarity=0.3,
            ),
            optimization_report=self._report(aggregate_risk=0.7),
        )

        self.assertEqual(result.decision, KEEP)
        self.assertFalse(result.dominance_approved)
        self.assertIn("Candidate does not dominate the target Alpha.", result.reasons)

    def test_engine_keep_quando_benchmark_e_insuficiente(self) -> None:
        result = PortfolioReplacementEngine().evaluate(
            candidate=self._candidate(
                portfolio_score=0.5,
                dominance=ALPHA_A_DOMINATES,
                similarity=0.3,
            ),
            optimization_report=self._report(aggregate_risk=0.7),
        )

        self.assertEqual(result.decision, KEEP)
        self.assertFalse(result.benchmark_approved)
        self.assertIn(
            "Benchmark score is below replacement threshold.",
            result.reasons,
        )

    def test_engine_wait_quando_domina_mas_similarity_ou_risco_bloqueia(self) -> None:
        result = PortfolioReplacementEngine().evaluate(
            candidate=self._candidate(
                portfolio_score=0.9,
                dominance=ALPHA_A_DOMINATES,
                similarity=0.9,
            ),
            optimization_report=self._report(aggregate_risk=1.2),
        )

        self.assertEqual(result.decision, WAIT)
        self.assertTrue(result.dominance_approved)
        self.assertTrue(result.benchmark_approved)
        self.assertFalse(result.similarity_approved)
        self.assertFalse(result.risk_approved)
        self.assertIn(
            "Candidate is too similar to replace with confidence.",
            result.reasons,
        )
        self.assertIn(
            "Aggregate portfolio risk is above threshold.",
            result.reasons,
        )

    def test_result_e_imutavel(self) -> None:
        result = PortfolioReplacementEngine().evaluate(
            candidate=self._candidate(0.85, ALPHA_A_DOMINATES, 0.35),
            optimization_report=self._report(0.8),
        )

        with self.assertRaises(FrozenInstanceError):
            result.decision = KEEP

    def test_engine_nao_remove_alphas_ou_altera_otimizacao(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_replacement_engine.py"))
        forbidden_fragments = (
            "remove(",
            "pop(",
            "del ",
            "unregister",
            "Allocation",
            "PortfolioOptimizationEngine",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            ".run(",
            ".optimize(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".next_candle(",
            ".generate_signal(",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_replacement_engine.py")
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
            "remove",
            "pop",
            "unregister",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.portfolio.portfolio_candidate", imports)
        self.assertIn("research.portfolio.portfolio_optimization_report", imports)

    def _candidate(
        self,
        portfolio_score: float,
        dominance: str,
        similarity: float,
    ) -> PortfolioCandidate:
        return PortfolioCandidate(
            candidate_id="candidate-alpha102-001",
            alpha_id="Alpha102",
            benchmark_result=self._benchmark_result(),
            validation_certification=self._certification(),
            portfolio_score=portfolio_score,
            current_status="PORTFOLIO_CANDIDATE",
            created_at="2026-06-28T14:45:00-03:00",
            metadata={
                "dominance_decision": dominance,
                "similarity_score": similarity,
            },
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
                created_at="2026-06-28T14:45:00-03:00",
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

    def _report(self, aggregate_risk: float) -> PortfolioOptimizationReport:
        optimization = PortfolioOptimizationResult(
            profile_id="portfolio-optimization-001",
            optimization_goal="BALANCED",
            allocation_method="RISK_ADJUSTED",
            selected_weights={"Alpha101": 0.4, "Alpha102": 0.2},
            equal_weight={"Alpha101": 0.3, "Alpha102": 0.3},
            risk_adjusted_weight={"Alpha101": 0.4, "Alpha102": 0.2},
            benchmark_recommendation="PORTFOLIO_CANDIDATE",
            execution_time=1.0,
            metadata={},
        )
        risk = PortfolioRiskResult(
            aggregate_risk=aggregate_risk,
            aggregate_drawdown=0.4,
            concentration_score=0.4,
            diversification_score=0.6,
        )
        simulation = AllocationSimulationResult(
            portfolio_equity_curve=(0.0, 1.0, 2.0),
            portfolio_return=2.0,
            portfolio_drawdown=0.1,
            portfolio_volatility=0.2,
        )
        return PortfolioOptimizationReport(
            optimization=optimization,
            risk=risk,
            simulation=simulation,
            optimization_goal=optimization.optimization_goal,
            allocation_method=optimization.allocation_method,
            alpha_weights=optimization.selected_weights,
            expected_return=simulation.portfolio_return,
            aggregate_drawdown=risk.aggregate_drawdown,
            diversification_score=risk.diversification_score,
            aggregate_risk=risk.aggregate_risk,
            execution_time=1.0,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
