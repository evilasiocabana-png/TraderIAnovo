"""Testes do motor oficial de otimizacao de portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.benchmark.alpha_dominance_engine import AlphaDominanceResult
from research.benchmark.alpha_similarity_engine import AlphaSimilarityResult
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationEngine,
    PortfolioOptimizationResult,
)
from research.portfolio.portfolio_optimization_profile import (
    PortfolioOptimizationProfile,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioOptimizationEngineTest(unittest.TestCase):
    """Valida otimizacao permitida sem recalcular pesos ou benchmark."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioOptimizationResult))
        self.assertTrue(PortfolioOptimizationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioOptimizationResult)],
            [
                "profile_id",
                "optimization_goal",
                "allocation_method",
                "selected_weights",
                "equal_weight",
                "risk_adjusted_weight",
                "benchmark_recommendation",
                "execution_time",
                "metadata",
            ],
        )

    def test_engine_seleciona_equal_weight(self) -> None:
        weights = self._weights()
        result = PortfolioOptimizationEngine().optimize(
            profile=self._profile(allocation_method="EQUAL_WEIGHT"),
            weights=weights,
            benchmark_report=self._benchmark_report(),
        )

        self.assertIs(result.selected_weights, weights.equal_weight)
        self.assertIs(result.equal_weight, weights.equal_weight)
        self.assertIs(result.risk_adjusted_weight, weights.risk_adjusted_weight)
        self.assertEqual(result.optimization_goal, "BALANCED")
        self.assertEqual(result.benchmark_recommendation, "KEEP_BOTH_FOR_RESEARCH")

    def test_engine_seleciona_risk_adjusted_weight(self) -> None:
        weights = self._weights()
        result = PortfolioOptimizationEngine().optimize(
            profile=self._profile(allocation_method="RISK_ADJUSTED"),
            weights=weights,
            benchmark_report=self._benchmark_report(),
        )

        self.assertIs(result.selected_weights, weights.risk_adjusted_weight)
        self.assertEqual(result.selected_weights["Alpha001"], 0.3)
        self.assertEqual(result.selected_weights["Alpha301"], 0.5)

    def test_engine_preserva_profile_weights_e_benchmark(self) -> None:
        profile = self._profile(allocation_method="RISK_ADJUSTED")
        weights = self._weights()
        benchmark = self._benchmark_report()

        result = PortfolioOptimizationEngine().optimize(profile, weights, benchmark)

        self.assertEqual(profile.allocation_method, "RISK_ADJUSTED")
        self.assertEqual(benchmark.recommendation, "KEEP_BOTH_FOR_RESEARCH")
        self.assertIs(result.metadata, profile.metadata)

    def test_result_e_imutavel(self) -> None:
        result = PortfolioOptimizationEngine().optimize(
            profile=self._profile(allocation_method="EQUAL_WEIGHT"),
            weights=self._weights(),
            benchmark_report=self._benchmark_report(),
        )

        with self.assertRaises(FrozenInstanceError):
            result.allocation_method = "RISK_ADJUSTED"

    def test_engine_nao_implementa_otimizacoes_proibidas(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_optimization_engine.py")
        )
        forbidden_fragments = (
            "Markowitz",
            "Black-Litterman",
            "HRP",
            "Risk Parity",
            "CVaR",
            "scipy",
            "numpy",
            "ResearchPipeline",
            "ResearchRunner",
            ".calculate(",
            ".compare(",
            "net_profit",
            "max_drawdown",
            "profit_factor",
            "win_rate",
            "expectancy",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_optimization_engine.py")
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
            "numpy",
            "scipy",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(
        self,
        allocation_method: str,
    ) -> PortfolioOptimizationProfile:
        return PortfolioOptimizationProfile(
            profile_id="portfolio-optimization-001",
            capital=100000.0,
            allocation_method=allocation_method,
            optimization_goal="BALANCED",
            alpha_ids=("Alpha001", "Alpha301"),
            constraints={"max_total_exposure": 0.8},
            created_at="2026-06-28T05:35:00-03:00",
            metadata={"source": "unit-test"},
        )

    def _weights(self) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha001": 0.4, "Alpha301": 0.4},
            risk_adjusted_weight={"Alpha001": 0.3, "Alpha301": 0.5},
        )

    def _benchmark_report(self) -> AlphaBenchmarkReport:
        benchmark = self._benchmark_result()
        dominance = AlphaDominanceResult(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            decision="ALPHA_B_DOMINATES",
            alpha_a_score=2,
            alpha_b_score=5,
            compared_metrics=("net_profit", "max_drawdown"),
        )
        similarity = AlphaSimilarityResult(
            similarity_score=0.4,
            overlap_score=0.2,
            diversification_score=0.6,
        )
        return AlphaBenchmarkReport(
            benchmark_result=benchmark,
            dominance=dominance,
            similarity=similarity,
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            benchmark_summary="Benchmark institucional.",
            dominance_result=dominance.decision,
            similarity_score=similarity.similarity_score,
            diversification_score=similarity.diversification_score,
            recommendation="KEEP_BOTH_FOR_RESEARCH",
            execution_time=1.5,
            metadata={},
        )

    def _benchmark_result(self) -> AlphaBenchmarkResult:
        comparison = AlphaBenchmarkComparison(
            alpha_id="Alpha301",
            experiment_id="exp-301",
            net_profit=80.0,
            max_drawdown=7.0,
            profit_factor=1.8,
            win_rate=0.6,
            expectancy=3.0,
            robustness=0.9,
            reproducibility=0.8,
        )
        return AlphaBenchmarkResult(
            profile=AlphaBenchmarkProfile(
                benchmark_id="benchmark-alpha001-alpha301",
                alpha_a="Alpha001",
                alpha_b="Alpha301",
                experiment_ids=("exp-001", "exp-301"),
                campaign_ids=("campaign-001", "campaign-301"),
                comparison_period="2026-01",
                metrics=("net_profit", "max_drawdown"),
                created_at="2026-06-28T05:35:00-03:00",
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


if __name__ == "__main__":
    unittest.main()
