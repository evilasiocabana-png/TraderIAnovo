"""Testes do posicionamento de benchmark da Alpha102."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.alpha102.alpha102_benchmark import (
    ALPHA102,
    DEFAULT_PEERS,
    Alpha102Benchmark,
    Alpha102BenchmarkResult,
    Alpha102PeerBenchmark,
)
from research.benchmark.alpha_dominance_engine import ALPHA_A_DOMINATES
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha102BenchmarkTest(unittest.TestCase):
    """Valida benchmark da Alpha102 contra o portfolio existente."""

    def test_resultados_sao_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha102PeerBenchmark))
        self.assertTrue(Alpha102PeerBenchmark.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(Alpha102BenchmarkResult))
        self.assertTrue(Alpha102BenchmarkResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Alpha102BenchmarkResult)],
            [
                "alpha_id",
                "peers",
                "peer_benchmarks",
                "dominance_summary",
                "similarity_summary",
                "portfolio_position",
            ],
        )

    def test_posiciona_alpha102_contra_quatro_alphas_oficiais(self) -> None:
        result = Alpha102Benchmark().position(
            alpha102_result=self._execution_result(
                net_profit=120.0,
                max_drawdown=5.0,
                profit_factor=2.0,
                win_rate=0.7,
                expectancy=4.0,
                robustness=0.9,
                reproducibility=0.9,
            ),
            peer_results={
                "Alpha101": self._execution_result(80.0, 9.0, 1.3, 0.55, 1.5),
                "Alpha001": self._execution_result(70.0, 12.0, 1.2, 0.50, 1.0),
                "Alpha002": self._execution_result(60.0, 10.0, 1.1, 0.48, 0.8),
                "Alpha003": self._execution_result(90.0, 7.0, 1.4, 0.58, 1.8),
            },
            comparison_period="2026-Q1",
            created_at="2026-06-28T13:45:00-03:00",
        )

        self.assertEqual(result.alpha_id, ALPHA102)
        self.assertEqual(result.peers, DEFAULT_PEERS)
        self.assertEqual(len(result.peer_benchmarks), 4)
        self.assertEqual(result.portfolio_position, "LEADING")
        self.assertTrue(
            all(
                decision == ALPHA_A_DOMINATES
                for decision in result.dominance_summary.values()
            )
        )

    def test_gera_relatorios_par_a_par_com_benchmark_dominancia_e_similaridade(self) -> None:
        result = Alpha102Benchmark().position(
            alpha102_result=self._execution_result(100.0, 8.0, 1.8, 0.62, 2.5),
            peer_results={"Alpha101": self._execution_result(90.0, 9.0, 1.5, 0.58, 2.0)},
            comparison_period="2026-Q1",
            created_at="2026-06-28T13:45:00-03:00",
        )

        peer = result.peer_benchmarks[0]
        report = peer.report

        self.assertEqual(peer.peer_alpha, "Alpha101")
        self.assertEqual(report.alpha_a, "Alpha102")
        self.assertEqual(report.alpha_b, "Alpha101")
        self.assertEqual(report.benchmark_result.profile.alpha_a, "Alpha102")
        self.assertEqual(report.benchmark_result.profile.alpha_b, "Alpha101")
        self.assertEqual(report.benchmark_result.total_results, 2)
        self.assertEqual(report.dominance.benchmark_id, "benchmark-alpha102-alpha101")
        self.assertGreaterEqual(report.similarity.similarity_score, 0.0)
        self.assertEqual(report.metadata["target_alpha"], "Alpha102")
        self.assertEqual(report.recommendation, "NEUTRAL")

    def test_retorna_unpositioned_quando_nao_ha_pares(self) -> None:
        result = Alpha102Benchmark().position(
            alpha102_result=self._execution_result(),
            peer_results={},
            comparison_period="2026-Q1",
            created_at="2026-06-28T13:45:00-03:00",
        )

        self.assertEqual(result.peers, ())
        self.assertEqual(result.peer_benchmarks, ())
        self.assertEqual(result.dominance_summary, {})
        self.assertEqual(result.similarity_summary, {})
        self.assertEqual(result.portfolio_position, "UNPOSITIONED")

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha102Benchmark().position(
            alpha102_result=self._execution_result(),
            peer_results={"Alpha101": self._execution_result()},
            comparison_period="2026-Q1",
            created_at="2026-06-28T13:45:00-03:00",
        )

        with self.assertRaises(FrozenInstanceError):
            result.portfolio_position = "LAGGING"

    def test_benchmark_nao_recalcula_metricas_ou_executa_research(self) -> None:
        source = read_source(Path("research/alpha102/alpha102_benchmark.py"))
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
            ".validate(",
            ".next_candle(",
            ".generate_signal(",
            "gross_profit_points =",
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

    def test_benchmark_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha102/alpha102_benchmark.py")
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
            "broker",
            "mt5",
            "MetaTrader5",
            "openai",
        }
        forbidden_calls = {
            "run",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.benchmark.alpha_benchmark_engine", imports)
        self.assertIn("research.benchmark.alpha_dominance_engine", imports)
        self.assertIn("research.benchmark.alpha_similarity_engine", imports)

    def _execution_result(
        self,
        net_profit: float = 0.0,
        max_drawdown: float = 0.0,
        profit_factor: float = 0.0,
        win_rate: float = 0.0,
        expectancy: float = 0.0,
        robustness: float = 0.0,
        reproducibility: float = 0.0,
    ) -> ResearchExecutionResult:
        research = Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(10, 4, 3, 3),
            profit=Alpha001ProfitResult(
                gross_profit_points=max(net_profit, 0.0),
                gross_loss_points=abs(min(net_profit, 0.0)),
                net_profit_points=net_profit,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0, net_profit),
                max_drawdown_points=max_drawdown,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(6, 3, 1, win_rate),
            profit_factor=Alpha001ProfitFactorResult(profit_factor),
            expectancy=Alpha001ExpectancyResult(0.0, 0.0, 0.0, expectancy),
        )
        result = ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(10, 10, 4, 3, 3, 0.0),
            metrics=research.metrics,
            profit=research.profit,
            drawdown=research.drawdown,
            win_rate=research.win_rate,
            profit_factor=research.profit_factor,
            expectancy=research.expectancy,
            benchmark=Alpha001BenchmarkResult(0, None, None, None, None, None, None, None),
            research_report=research,
            validation=Alpha001ResearchValidationResult(
                approved=True,
                status="APPROVED",
                reasons=(),
                minimum_trades=1,
                minimum_profit_factor=1.0,
                maximum_drawdown=10.0,
                minimum_win_rate=0.1,
                real_trading_authorized=False,
            ),
            recommendation=Alpha001ResearchRecommendation(
                recommendation="APPROVED_FOR_MORE_RESEARCH",
                status="APPROVED",
                reasons=(),
                real_trading_authorized=False,
            ),
            stage_results=(),
            started_at=datetime(2026, 6, 28, 13, 45, 0),
            finished_at=datetime(2026, 6, 28, 13, 46, 0),
            duration=60.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )
        object.__setattr__(result, "robustness_score", robustness)
        object.__setattr__(result, "reproducibility_score", reproducibility)
        return result


if __name__ == "__main__":
    unittest.main()
