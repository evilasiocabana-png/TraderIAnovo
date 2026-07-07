"""Testes do engine de benchmark entre Alphas."""

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
from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkEngine,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaBenchmarkEngineTest(unittest.TestCase):
    """Valida comparacao entre Alphas sem recalculo de metricas."""

    def test_resultados_sao_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaBenchmarkComparison))
        self.assertTrue(AlphaBenchmarkComparison.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(AlphaBenchmarkResult))
        self.assertTrue(AlphaBenchmarkResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaBenchmarkResult)],
            [
                "profile",
                "total_results",
                "comparisons",
                "best_net_profit",
                "best_max_drawdown",
                "best_profit_factor",
                "best_win_rate",
                "best_expectancy",
                "best_robustness",
                "best_reproducibility",
            ],
        )

    def test_compare_consolida_metricas_existentes(self) -> None:
        alpha001 = self._execution_result(
            net_profit=50.0,
            max_drawdown=10.0,
            profit_factor=1.4,
            win_rate=0.55,
            expectancy=2.0,
            robustness=0.7,
            reproducibility=0.8,
        )
        alpha301 = self._execution_result(
            net_profit=80.0,
            max_drawdown=7.0,
            profit_factor=1.8,
            win_rate=0.6,
            expectancy=3.0,
            robustness=0.9,
            reproducibility=0.75,
        )

        result = AlphaBenchmarkEngine().compare(
            profile=self._profile(),
            results=(alpha001, alpha301),
        )

        self.assertEqual(result.total_results, 2)
        self.assertEqual(result.comparisons[0].alpha_id, "Alpha001")
        self.assertEqual(result.comparisons[1].alpha_id, "Alpha301")
        self.assertEqual(result.comparisons[0].experiment_id, "exp-001")
        self.assertEqual(result.comparisons[1].experiment_id, "exp-301")
        self.assertEqual(result.best_net_profit.alpha_id, "Alpha301")
        self.assertEqual(result.best_max_drawdown.alpha_id, "Alpha301")
        self.assertEqual(result.best_profit_factor.alpha_id, "Alpha301")
        self.assertEqual(result.best_win_rate.alpha_id, "Alpha301")
        self.assertEqual(result.best_expectancy.alpha_id, "Alpha301")
        self.assertEqual(result.best_robustness.alpha_id, "Alpha301")
        self.assertEqual(result.best_reproducibility.alpha_id, "Alpha001")

    def test_compare_retorna_resultado_vazio(self) -> None:
        result = AlphaBenchmarkEngine().compare(self._profile(), ())

        self.assertEqual(result.total_results, 0)
        self.assertEqual(result.comparisons, ())
        self.assertIsNone(result.best_net_profit)
        self.assertIsNone(result.best_max_drawdown)
        self.assertIsNone(result.best_profit_factor)
        self.assertIsNone(result.best_win_rate)
        self.assertIsNone(result.best_expectancy)
        self.assertIsNone(result.best_robustness)
        self.assertIsNone(result.best_reproducibility)

    def test_scores_de_robustez_e_reprodutibilidade_tem_fallback_seguro(self) -> None:
        result = AlphaBenchmarkEngine().compare(
            profile=self._profile(),
            results=(self._execution_result(),),
        )

        self.assertEqual(result.comparisons[0].robustness, 0.0)
        self.assertEqual(result.comparisons[0].reproducibility, 0.0)

    def test_comparison_e_imutavel(self) -> None:
        result = AlphaBenchmarkEngine().compare(
            profile=self._profile(),
            results=(self._execution_result(net_profit=10.0),),
        )

        with self.assertRaises(FrozenInstanceError):
            result.comparisons[0].net_profit = 1.0

    def test_engine_nao_recalcula_metricas_ou_altera_reports(self) -> None:
        source = read_source(Path("research/benchmark/alpha_benchmark_engine.py"))
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
            ".calculate(",
            ".validate(",
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

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/benchmark/alpha_benchmark_engine.py")
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
        }
        forbidden_calls = {
            "run",
            "calculate",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

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
            created_at="2026-06-28T05:10:00-03:00",
            metadata={},
        )

    def _execution_result(
        self,
        net_profit: float = 0.0,
        max_drawdown: float = 0.0,
        profit_factor: float = 0.0,
        win_rate: float = 0.0,
        expectancy: float = 0.0,
        robustness: float | None = None,
        reproducibility: float | None = None,
    ) -> ResearchExecutionResult:
        research = Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(10, 5, 5, 0),
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
            win_rate=Alpha001WinRateResult(5, 5, 0, win_rate),
            profit_factor=Alpha001ProfitFactorResult(profit_factor),
            expectancy=Alpha001ExpectancyResult(0.0, 0.0, 0.0, expectancy),
        )
        result = ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(10, 10, 5, 5, 0, 0.0),
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
            started_at=datetime(2026, 6, 28, 5, 10, 0),
            finished_at=datetime(2026, 6, 28, 5, 11, 0),
            duration=60.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )
        if robustness is not None:
            object.__setattr__(result, "robustness_score", robustness)
        if reproducibility is not None:
            object.__setattr__(result, "reproducibility_score", reproducibility)
        return result


if __name__ == "__main__":
    unittest.main()
