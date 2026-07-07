"""Testes do engine de similaridade entre Alphas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_similarity_engine import (
    AlphaSimilarityEngine,
    AlphaSimilarityResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaSimilarityEngineTest(unittest.TestCase):
    """Valida medicao de similaridade sem recalcular metricas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaSimilarityResult))
        self.assertTrue(AlphaSimilarityResult.__dataclass_params__.frozen)

    def test_result_define_apenas_scores_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaSimilarityResult)],
            [
                "similarity_score",
                "overlap_score",
                "diversification_score",
            ],
        )

    def test_calcula_alta_similaridade_para_alphas_redundantes(self) -> None:
        result = AlphaSimilarityEngine().calculate(
            self._benchmark_result(
                alpha_a=self._comparison(
                    "Alpha001",
                    net_profit=100.0,
                    max_drawdown=10.0,
                    profit_factor=1.5,
                    win_rate=0.60,
                    expectancy=2.0,
                    robustness=0.80,
                    reproducibility=0.90,
                ),
                alpha_b=self._comparison(
                    "Alpha301",
                    net_profit=95.0,
                    max_drawdown=11.0,
                    profit_factor=1.4,
                    win_rate=0.58,
                    expectancy=1.9,
                    robustness=0.78,
                    reproducibility=0.88,
                ),
            )
        )

        self.assertGreater(result.similarity_score, 0.9)
        self.assertEqual(result.overlap_score, 1.0)
        self.assertLess(result.diversification_score, 0.1)

    def test_calcula_baixa_similaridade_para_alphas_diversificadas(self) -> None:
        result = AlphaSimilarityEngine().calculate(
            self._benchmark_result(
                alpha_a=self._comparison(
                    "Alpha001",
                    net_profit=100.0,
                    max_drawdown=5.0,
                    profit_factor=2.0,
                    win_rate=0.8,
                    expectancy=5.0,
                    robustness=1.0,
                    reproducibility=1.0,
                ),
                alpha_b=self._comparison(
                    "Alpha301",
                    net_profit=-50.0,
                    max_drawdown=30.0,
                    profit_factor=0.5,
                    win_rate=0.2,
                    expectancy=-2.0,
                    robustness=0.2,
                    reproducibility=0.3,
                ),
            )
        )

        self.assertLess(result.similarity_score, 0.6)
        self.assertLess(result.overlap_score, 0.5)
        self.assertGreater(result.diversification_score, 0.4)

    def test_resultado_vazio_retorna_sem_overlap_e_diversificacao_maxima(self) -> None:
        result = AlphaSimilarityEngine().calculate(
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

        self.assertEqual(result.similarity_score, 0.0)
        self.assertEqual(result.overlap_score, 0.0)
        self.assertEqual(result.diversification_score, 1.0)

    def test_result_e_imutavel(self) -> None:
        result = AlphaSimilarityEngine().calculate(
            self._benchmark_result(
                self._comparison("Alpha001"),
                self._comparison("Alpha301"),
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.similarity_score = 0.0

    def test_engine_nao_recalcula_metricas_ou_altera_benchmark(self) -> None:
        source = read_source(Path("research/benchmark/alpha_similarity_engine.py"))
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".compare(",
            "net_profit_points",
            "max_drawdown_points",
            "profit_factor =",
            "win_rate =",
            "expectancy =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/benchmark/alpha_similarity_engine.py")
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
        return AlphaBenchmarkResult(
            profile=self._profile(),
            total_results=2,
            comparisons=(alpha_a, alpha_b),
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
            created_at="2026-06-28T05:20:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
