"""Testes do engine de dominancia entre Alphas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_dominance_engine import (
    ALPHA_A_DOMINATES,
    ALPHA_B_DOMINATES,
    TIE,
    AlphaDominanceEngine,
    AlphaDominanceResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaDominanceEngineTest(unittest.TestCase):
    """Valida decisao de dominancia baseada em metricas comparadas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaDominanceResult))
        self.assertTrue(AlphaDominanceResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaDominanceResult)],
            [
                "benchmark_id",
                "alpha_a",
                "alpha_b",
                "decision",
                "alpha_a_score",
                "alpha_b_score",
                "compared_metrics",
            ],
        )

    def test_alpha_a_domina_quando_vence_maioria_das_metricas(self) -> None:
        result = AlphaDominanceEngine().decide(
            self._benchmark_result(
                alpha_a=self._comparison(
                    "Alpha001",
                    net_profit=100.0,
                    max_drawdown=4.0,
                    profit_factor=1.8,
                    win_rate=0.6,
                    expectancy=3.0,
                    robustness=0.8,
                    reproducibility=0.9,
                ),
                alpha_b=self._comparison(
                    "Alpha301",
                    net_profit=80.0,
                    max_drawdown=7.0,
                    profit_factor=1.2,
                    win_rate=0.5,
                    expectancy=2.0,
                    robustness=0.7,
                    reproducibility=0.8,
                ),
            )
        )

        self.assertEqual(result.decision, ALPHA_A_DOMINATES)
        self.assertEqual(result.alpha_a_score, 7)
        self.assertEqual(result.alpha_b_score, 0)

    def test_alpha_b_domina_quando_vence_maioria_das_metricas(self) -> None:
        result = AlphaDominanceEngine().decide(
            self._benchmark_result(
                alpha_a=self._comparison(
                    "Alpha001",
                    net_profit=50.0,
                    max_drawdown=12.0,
                    profit_factor=1.1,
                    win_rate=0.4,
                    expectancy=1.0,
                    robustness=0.6,
                    reproducibility=0.7,
                ),
                alpha_b=self._comparison(
                    "Alpha301",
                    net_profit=90.0,
                    max_drawdown=6.0,
                    profit_factor=1.6,
                    win_rate=0.55,
                    expectancy=2.5,
                    robustness=0.8,
                    reproducibility=0.9,
                ),
            )
        )

        self.assertEqual(result.decision, ALPHA_B_DOMINATES)
        self.assertEqual(result.alpha_a_score, 0)
        self.assertEqual(result.alpha_b_score, 7)

    def test_empate_quando_scores_sao_iguais(self) -> None:
        result = AlphaDominanceEngine().decide(
            self._benchmark_result(
                alpha_a=self._comparison(
                    "Alpha001",
                    net_profit=100.0,
                    max_drawdown=8.0,
                    profit_factor=1.5,
                    win_rate=0.5,
                    expectancy=2.0,
                    robustness=0.7,
                    reproducibility=0.8,
                ),
                alpha_b=self._comparison(
                    "Alpha301",
                    net_profit=90.0,
                    max_drawdown=8.0,
                    profit_factor=1.6,
                    win_rate=0.5,
                    expectancy=3.0,
                    robustness=0.7,
                    reproducibility=0.7,
                ),
            )
        )

        self.assertEqual(result.decision, TIE)
        self.assertEqual(result.alpha_a_score, 2)
        self.assertEqual(result.alpha_b_score, 2)

    def test_resultado_vazio_retorna_empate(self) -> None:
        result = AlphaDominanceEngine().decide(
            AlphaBenchmarkResult(
                profile=self._profile(),
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
        )

        self.assertEqual(result.decision, TIE)
        self.assertEqual(result.alpha_a_score, 0)
        self.assertEqual(result.alpha_b_score, 0)

    def test_result_e_imutavel(self) -> None:
        result = AlphaDominanceEngine().decide(
            self._benchmark_result(
                self._comparison("Alpha001"),
                self._comparison("Alpha301"),
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.decision = ALPHA_A_DOMINATES

    def test_engine_nao_usa_ia_ou_altera_benchmark(self) -> None:
        source = read_source(Path("research/benchmark/alpha_dominance_engine.py"))
        forbidden_fragments = (
            "openai",
            "llm",
            "machine learning",
            "ResearchPipeline",
            "ResearchRunner",
            "Dashboard",
            "streamlit",
            ".run(",
            ".calculate(",
            ".compare(",
            "benchmark_result =",
            "benchmark_result.",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment != "benchmark_result."
            and fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/benchmark/alpha_dominance_engine.py")
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

    def _benchmark_result(
        self,
        alpha_a: AlphaBenchmarkComparison,
        alpha_b: AlphaBenchmarkComparison,
    ) -> AlphaBenchmarkResult:
        comparisons = (alpha_a, alpha_b)
        return AlphaBenchmarkResult(
            profile=self._profile(),
            total_results=2,
            comparisons=comparisons,
            best_net_profit=None,
            best_max_drawdown=None,
            best_profit_factor=None,
            best_win_rate=None,
            best_expectancy=None,
            best_robustness=None,
            best_reproducibility=None,
        )

    def _comparison(
        self,
        alpha_id: str,
        net_profit: float = 0.0,
        max_drawdown: float = 0.0,
        profit_factor: float = 0.0,
        win_rate: float = 0.0,
        expectancy: float = 0.0,
        robustness: float = 0.0,
        reproducibility: float = 0.0,
    ) -> AlphaBenchmarkComparison:
        return AlphaBenchmarkComparison(
            alpha_id=alpha_id,
            experiment_id=f"exp-{alpha_id.lower()}",
            net_profit=net_profit,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            win_rate=win_rate,
            expectancy=expectancy,
            robustness=robustness,
            reproducibility=reproducibility,
        )

    def _profile(self) -> AlphaBenchmarkProfile:
        return AlphaBenchmarkProfile(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            experiment_ids=("exp-001", "exp-301"),
            campaign_ids=("campaign-001", "campaign-301"),
            comparison_period="2026-01",
            metrics=(
                "net_profit",
                "max_drawdown",
                "profit_factor",
                "win_rate",
                "expectancy",
                "robustness",
                "reproducibility",
            ),
            created_at="2026-06-28T05:15:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
