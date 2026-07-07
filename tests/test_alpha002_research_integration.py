"""Testes de integracao da Alpha002 com a infraestrutura de Research."""

from pathlib import Path
import unittest

from domain.candle import Candle
from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.alpha002.alpha002_experiment import Alpha002Experiment
from research.research_execution_plan import (
    ResearchExecutionPlan,
    ResearchExecutionStep,
)
from research.research_pipeline import ResearchPipeline, ResearchPipelineResult
from research.research_runner import ResearchRunner
from research.research_stage import ResearchStage
from strategies.alpha002.alpha002_config import Alpha002Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha002ResearchIntegrationTest(unittest.TestCase):
    """Valida reaproveitamento da arquitetura de Research pela Alpha002."""

    def test_research_pipeline_executa_alpha002_com_engines_existentes(self) -> None:
        calls: list[str] = []
        pipeline = ResearchPipeline(
            metrics_engine=_SpyCalculate("metrics", calls, self._metrics()),
            profit_engine=_SpyCalculate("profit", calls, self._profit()),
            drawdown_engine=_SpyCalculate("drawdown", calls, self._drawdown()),
            win_rate_engine=_SpyCalculate("win_rate", calls, self._win_rate()),
            profit_factor_engine=_SpyCalculate(
                "profit_factor",
                calls,
                self._profit_factor(),
            ),
            expectancy_engine=_SpyCalculate("expectancy", calls, self._expectancy()),
            benchmark_comparator=_SpyComparator(calls),
            validator=_SpyValidator(calls, self._validation()),
            advisor=_SpyAdvisor(calls, self._recommendation()),
        )

        result = pipeline.run_alpha002(self._experiment())

        self.assertIsInstance(result, ResearchPipelineResult)
        self.assertEqual(
            calls,
            [
                "metrics",
                "profit",
                "drawdown",
                "win_rate",
                "profit_factor",
                "expectancy",
                "benchmark",
                "validator",
                "advisor",
            ],
        )
        self.assertEqual(result.experiment.total_candles, 2)
        self.assertIsInstance(result.research, Alpha001ResearchResult)

    def test_research_runner_reconhece_etapa_alpha002_experiment(self) -> None:
        calls: list[str] = []
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep(
                    name="Alpha002Experiment",
                    order=1,
                    description="Executa experimento estrutural da Alpha002.",
                    enabled=True,
                    required=True,
                ),
                ResearchExecutionStep(
                    name="Alpha001MetricsEngine",
                    order=2,
                    description="Reutiliza MetricsEngine existente.",
                    enabled=True,
                    required=True,
                ),
            ),
        )
        runner = ResearchRunner(
            plan=plan,
            metrics_engine=_SpyCalculate("metrics", calls, self._metrics()),
        )

        result = runner.run(_ExperimentSpy(calls))

        self.assertEqual(calls, ["experiment", "metrics"])
        self.assertEqual(result.status, ResearchStage.COMPLETED)
        self.assertEqual(len(result.stage_results), 2)
        self.assertTrue(all(stage.success for stage in result.stage_results))

    def test_alpha002_nao_cria_engines_de_pesquisa_proprios(self) -> None:
        alpha002_files = [
            Path("research/alpha002/__init__.py"),
            Path("research/alpha002/alpha002_experiment.py"),
        ]
        forbidden_fragments = (
            "MetricsEngine",
            "ProfitEngine",
            "DrawdownEngine",
            "WinRateEngine",
            "ProfitFactorEngine",
            "ExpectancyEngine",
            "calculate_profit",
            "calculate_drawdown",
            "calculate_win_rate",
            "calculate_profit_factor",
        )

        leaked: list[str] = []
        for path in alpha002_files:
            source = read_source(path)
            leaked.extend(
                f"{path}:{fragment}"
                for fragment in forbidden_fragments
                if fragment in source
            )

        self.assertEqual(leaked, [])

    def test_integracao_nao_altera_pipelines_operacionais(self) -> None:
        checked_paths = (
            Path("research/research_pipeline.py"),
            Path("research/research_runner.py"),
        )
        forbidden_imports = {
            "core.decision_pipeline",
            "replay.replay_engine",
            "market.features.feature_pipeline",
            "market.context.context_pipeline",
            "risk.risk_pipeline",
            "market.data.data_pipeline",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "order_send",
            "execute_order",
            "send_order",
            "next_candle",
            "processar",
        }

        for path in checked_paths:
            with self.subTest(path=str(path)):
                self.assertTrue(forbidden_imports.isdisjoint(imports_from(path)))
                self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def _experiment(self) -> Alpha002Experiment:
        return Alpha002Experiment(
            config=self._config(),
            candles=(
                Candle("2026-06-27T10:00:00-03:00", 5500.0, 5520.0, 5480.0, 5485.0, 2000),
                Candle("2026-06-27T10:01:00-03:00", 5500.0, 5530.0, 5490.0, 5520.0, 2100),
            ),
        )

    def _config(self) -> Alpha002Config:
        return Alpha002Config(
            opening_range=15,
            stop_points=50.0,
            target_points=100.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            session_start="09:00",
            session_end="18:00",
        )

    def _metrics(self) -> Alpha001MetricsResult:
        return Alpha001MetricsResult(2, 1, 1, 0)

    def _profit(self) -> Alpha001ProfitResult:
        return Alpha001ProfitResult(10.0, 5.0, 5.0)

    def _drawdown(self) -> Alpha001DrawdownResult:
        return Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0)

    def _win_rate(self) -> Alpha001WinRateResult:
        return Alpha001WinRateResult(1, 1, 0, 0.5)

    def _profit_factor(self) -> Alpha001ProfitFactorResult:
        return Alpha001ProfitFactorResult(2.0)

    def _expectancy(self) -> Alpha001ExpectancyResult:
        return Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0)

    def _validation(self) -> Alpha001ResearchValidationResult:
        return Alpha001ResearchValidationResult(
            approved=True,
            status="APPROVED",
            reasons=("ok",),
            minimum_trades=1,
            minimum_profit_factor=1.0,
            maximum_drawdown=10.0,
            minimum_win_rate=0.1,
            real_trading_authorized=False,
        )

    def _recommendation(self) -> Alpha001ResearchRecommendation:
        return Alpha001ResearchRecommendation(
            recommendation="APPROVED_FOR_MORE_RESEARCH",
            status="APPROVED",
            reasons=("ok",),
            real_trading_authorized=False,
        )


class _ExperimentSpy:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def run(self) -> object:
        self.calls.append("experiment")
        return object()


class _SpyCalculate:
    def __init__(self, name: str, calls: list[str], result: object) -> None:
        self.name = name
        self.calls = calls
        self.result = result

    def calculate(self, value: object) -> object:
        self.calls.append(self.name)
        return self.result


class _SpyComparator:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def compare(
        self,
        results: list[Alpha001ResearchResult],
    ) -> Alpha001BenchmarkResult:
        self.calls.append("benchmark")
        best = results[0] if results else None
        return Alpha001BenchmarkResult(
            total_results=len(results),
            best_overall=best,
            best_total_trades=best,
            best_net_profit=best,
            best_max_drawdown=best,
            best_profit_factor=best,
            best_win_rate=best,
            best_expectancy=best,
            ranking=tuple(results),
        )


class _SpyValidator:
    def __init__(
        self,
        calls: list[str],
        result: Alpha001ResearchValidationResult,
    ) -> None:
        self.calls = calls
        self.result = result

    def validate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001ResearchValidationResult:
        self.calls.append("validator")
        return self.result


class _SpyAdvisor:
    def __init__(
        self,
        calls: list[str],
        result: Alpha001ResearchRecommendation,
    ) -> None:
        self.calls = calls
        self.result = result

    def recommend(
        self,
        validation_result: Alpha001ResearchValidationResult,
    ) -> Alpha001ResearchRecommendation:
        self.calls.append("advisor")
        return self.result


if __name__ == "__main__":
    unittest.main()
