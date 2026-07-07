"""Testes da avaliacao de portfolio da Alpha102."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.alpha102.alpha102_benchmark import (
    Alpha102BenchmarkResult,
    Alpha102PeerBenchmark,
)
from research.alpha102.alpha102_portfolio_evaluation import (
    CONTINUE_RESEARCH,
    REJECT_AS_REDUNDANT,
    REJECT_PORTFOLIO_IMPACT,
    Alpha102PortfolioEvaluation,
    Alpha102PortfolioEvaluationResult,
)
from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.benchmark.alpha_dominance_engine import (
    ALPHA_A_DOMINATES,
    ALPHA_B_DOMINATES,
    AlphaDominanceResult,
)
from research.benchmark.alpha_similarity_engine import AlphaSimilarityResult
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha102PortfolioEvaluationTest(unittest.TestCase):
    """Valida decisao oficial da Alpha Factory para Alpha102."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha102PortfolioEvaluationResult))
        self.assertTrue(Alpha102PortfolioEvaluationResult.__dataclass_params__.frozen)

    def test_result_define_apenas_respostas_institucionais(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Alpha102PortfolioEvaluationResult)],
            [
                "improves_portfolio",
                "worsens_portfolio",
                "is_redundant",
                "should_continue",
                "official_decision",
                "metadata",
            ],
        )

    def test_decide_que_alpha102_melhora_portfolio_e_deve_continuar(self) -> None:
        result = Alpha102PortfolioEvaluation().evaluate(
            allocation=self._allocation(alpha102_weight=0.25),
            optimization=self._optimization(alpha102_weight=0.25),
            benchmark=self._benchmark(
                dominance={
                    "Alpha101": ALPHA_A_DOMINATES,
                    "Alpha001": ALPHA_A_DOMINATES,
                    "Alpha002": ALPHA_A_DOMINATES,
                    "Alpha003": ALPHA_A_DOMINATES,
                },
                similarities={
                    "Alpha101": 0.3,
                    "Alpha001": 0.4,
                    "Alpha002": 0.5,
                    "Alpha003": 0.2,
                },
            ),
        )

        self.assertTrue(result.improves_portfolio)
        self.assertFalse(result.worsens_portfolio)
        self.assertFalse(result.is_redundant)
        self.assertTrue(result.should_continue)
        self.assertEqual(result.official_decision, CONTINUE_RESEARCH)

    def test_decide_que_alpha102_piora_portfolio(self) -> None:
        result = Alpha102PortfolioEvaluation().evaluate(
            allocation=self._allocation(alpha102_weight=0.2),
            optimization=self._optimization(alpha102_weight=0.2),
            benchmark=self._benchmark(
                dominance={
                    "Alpha101": ALPHA_B_DOMINATES,
                    "Alpha001": ALPHA_B_DOMINATES,
                    "Alpha002": ALPHA_B_DOMINATES,
                    "Alpha003": ALPHA_A_DOMINATES,
                },
                similarities={
                    "Alpha101": 0.2,
                    "Alpha001": 0.3,
                    "Alpha002": 0.4,
                    "Alpha003": 0.5,
                },
            ),
        )

        self.assertFalse(result.improves_portfolio)
        self.assertTrue(result.worsens_portfolio)
        self.assertFalse(result.is_redundant)
        self.assertFalse(result.should_continue)
        self.assertEqual(result.official_decision, REJECT_PORTFOLIO_IMPACT)

    def test_decide_que_alpha102_e_redundante(self) -> None:
        result = Alpha102PortfolioEvaluation().evaluate(
            allocation=self._allocation(alpha102_weight=0.2),
            optimization=self._optimization(alpha102_weight=0.2),
            benchmark=self._benchmark(
                dominance={
                    "Alpha101": ALPHA_A_DOMINATES,
                    "Alpha001": ALPHA_A_DOMINATES,
                    "Alpha002": ALPHA_A_DOMINATES,
                    "Alpha003": ALPHA_A_DOMINATES,
                },
                similarities={
                    "Alpha101": 0.9,
                    "Alpha001": 0.85,
                    "Alpha002": 0.88,
                    "Alpha003": 0.91,
                },
            ),
        )

        self.assertFalse(result.improves_portfolio)
        self.assertFalse(result.worsens_portfolio)
        self.assertTrue(result.is_redundant)
        self.assertFalse(result.should_continue)
        self.assertEqual(result.official_decision, REJECT_AS_REDUNDANT)

    def test_usa_allocation_como_fallback_quando_otimizacao_nao_tem_alpha102(self) -> None:
        result = Alpha102PortfolioEvaluation().evaluate(
            allocation=self._allocation(alpha102_weight=0.15),
            optimization=self._optimization(alpha102_weight=0.0, include_alpha102=False),
            benchmark=self._benchmark(
                dominance={"Alpha101": ALPHA_A_DOMINATES},
                similarities={"Alpha101": 0.3},
            ),
        )

        self.assertTrue(result.improves_portfolio)
        self.assertEqual(result.metadata["allocation_weight"], 0.15)

    def test_result_e_imutavel(self) -> None:
        result = Alpha102PortfolioEvaluation().evaluate(
            allocation=self._allocation(alpha102_weight=0.2),
            optimization=self._optimization(alpha102_weight=0.2),
            benchmark=self._benchmark(
                dominance={"Alpha101": ALPHA_A_DOMINATES},
                similarities={"Alpha101": 0.3},
            ),
        )

        with self.assertRaises(FrozenInstanceError):
            result.should_continue = False

    def test_evaluation_nao_recalcula_metricas_ou_executa_componentes(self) -> None:
        source = read_source(Path("research/alpha102/alpha102_portfolio_evaluation.py"))
        forbidden_fragments = (
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
            ".evaluate(",
            ".next_candle(",
            ".generate_signal(",
            "net_profit_points =",
            "max_drawdown_points =",
            "profit_factor =",
            "win_rate =",
            "expectancy =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_evaluation_permanece_desacoplada_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha102/alpha102_portfolio_evaluation.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
            "openai",
        }
        forbidden_calls = {
            "run",
            "optimize",
            "calculate",
            "compare",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.portfolio.allocation_weight_engine", imports)
        self.assertIn("research.portfolio.portfolio_optimization_engine", imports)
        self.assertIn("research.alpha102.alpha102_benchmark", imports)

    def _allocation(self, alpha102_weight: float) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha102": alpha102_weight, "Alpha101": 0.2},
            risk_adjusted_weight={"Alpha102": alpha102_weight, "Alpha101": 0.2},
        )

    def _optimization(
        self,
        alpha102_weight: float,
        include_alpha102: bool = True,
    ) -> PortfolioOptimizationResult:
        selected_weights = {"Alpha101": 0.2}
        if include_alpha102:
            selected_weights["Alpha102"] = alpha102_weight
        return PortfolioOptimizationResult(
            profile_id="portfolio-alpha102-evaluation",
            optimization_goal="BALANCED",
            allocation_method="RISK_ADJUSTED",
            selected_weights=selected_weights,
            equal_weight={"Alpha102": alpha102_weight, "Alpha101": 0.2},
            risk_adjusted_weight={"Alpha102": alpha102_weight, "Alpha101": 0.2},
            benchmark_recommendation="PORTFOLIO_CANDIDATE",
            execution_time=1.0,
            metadata={"source": "unit-test"},
        )

    def _benchmark(
        self,
        dominance: dict[str, str],
        similarities: dict[str, float],
    ) -> Alpha102BenchmarkResult:
        return Alpha102BenchmarkResult(
            alpha_id="Alpha102",
            peers=tuple(dominance),
            peer_benchmarks=tuple(
                Alpha102PeerBenchmark(
                    peer_alpha=peer,
                    report=self._report(peer, decision, similarities[peer]),
                )
                for peer, decision in dominance.items()
            ),
            dominance_summary=dominance,
            similarity_summary=similarities,
            portfolio_position="LEADING",
        )

    def _report(
        self,
        peer: str,
        dominance: str,
        similarity: float,
    ) -> AlphaBenchmarkReport:
        benchmark = AlphaBenchmarkResult(
            profile=AlphaBenchmarkProfile(
                benchmark_id=f"benchmark-alpha102-{peer.lower()}",
                alpha_a="Alpha102",
                alpha_b=peer,
                experiment_ids=("exp-alpha102", f"exp-{peer.lower()}"),
                campaign_ids=("campaign-alpha102", f"campaign-{peer.lower()}"),
                comparison_period="2026-Q1",
                metrics=("net_profit", "max_drawdown"),
                created_at="2026-06-28T14:00:00-03:00",
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
        dominance_result = AlphaDominanceResult(
            benchmark_id=benchmark.profile.benchmark_id,
            alpha_a="Alpha102",
            alpha_b=peer,
            decision=dominance,
            alpha_a_score=1 if dominance == ALPHA_A_DOMINATES else 0,
            alpha_b_score=1 if dominance == ALPHA_B_DOMINATES else 0,
            compared_metrics=("net_profit", "max_drawdown"),
        )
        similarity_result = AlphaSimilarityResult(
            similarity_score=similarity,
            overlap_score=similarity,
            diversification_score=1.0 - similarity,
        )
        return AlphaBenchmarkReport(
            benchmark_result=benchmark,
            dominance=dominance_result,
            similarity=similarity_result,
            alpha_a="Alpha102",
            alpha_b=peer,
            benchmark_summary="Benchmark Alpha102.",
            dominance_result=dominance,
            similarity_score=similarity,
            diversification_score=1.0 - similarity,
            recommendation="PORTFOLIO_CANDIDATE",
            execution_time=0.0,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
