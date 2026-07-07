"""Testes do executor oficial do Research Pipeline."""

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
from research.research_execution_plan import (
    ResearchExecutionPlan,
    ResearchExecutionStep,
)
from research.research_execution_result import ResearchExecutionResult
from research.research_runner import ResearchRunner
from research.research_stage import ResearchStage
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchRunnerTest(unittest.TestCase):
    """Valida execucao sequencial do plano de pesquisa."""

    def test_run_retorna_research_execution_result(self) -> None:
        result = ResearchRunner(plan=ResearchExecutionPlan()).run(
            _ExperimentSpy([]),
        )

        self.assertIsInstance(result, ResearchExecutionResult)
        self.assertEqual(result.status, ResearchStage.COMPLETED)
        self.assertEqual(result.errors, ())
        self.assertEqual(len(result.stage_results), 11)

    def test_executa_etapas_na_ordem_do_plano(self) -> None:
        calls: list[str] = []
        profit = Alpha001ProfitResult(10.0, 5.0, 5.0)
        validation = self._validation()
        runner = ResearchRunner(
            plan=ResearchExecutionPlan(),
            metrics_engine=_CalculateSpy("metrics", calls, self._metrics()),
            profit_engine=_CalculateSpy("profit", calls, profit),
            drawdown_engine=_CalculateSpy("drawdown", calls, self._drawdown()),
            win_rate_engine=_CalculateSpy("win_rate", calls, self._win_rate()),
            profit_factor_engine=_CalculateSpy(
                "profit_factor",
                calls,
                self._profit_factor(),
                expected_input=profit,
            ),
            expectancy_engine=_CalculateSpy("expectancy", calls, self._expectancy()),
            benchmark_comparator=_ComparatorSpy(calls),
            validator=_ValidatorSpy(calls, validation),
            advisor=_AdvisorSpy(calls, self._recommendation(), validation),
        )

        result = runner.run(_ExperimentSpy(calls))

        self.assertEqual(
            calls,
            [
                "experiment",
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
        self.assertTrue(all(stage.success for stage in result.stage_results))

    def test_interrompe_quando_etapa_obrigatoria_falha(self) -> None:
        calls: list[str] = []
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep(
                    name="Alpha001Experiment",
                    order=1,
                    description="Experiment",
                    enabled=True,
                    required=True,
                ),
                ResearchExecutionStep(
                    name="Alpha001MetricsEngine",
                    order=2,
                    description="Metrics",
                    enabled=True,
                    required=True,
                ),
                ResearchExecutionStep(
                    name="Alpha001ProfitEngine",
                    order=3,
                    description="Profit",
                    enabled=True,
                    required=True,
                ),
            ),
        )
        runner = ResearchRunner(
            plan=plan,
            metrics_engine=_FailingCalculateSpy("metrics", calls),
            profit_engine=_CalculateSpy("profit", calls, self._profit()),
        )

        result = runner.run(_ExperimentSpy(calls))

        self.assertEqual(calls, ["experiment", "metrics"])
        self.assertEqual(result.status, ResearchStage.FAILED)
        self.assertEqual(len(result.stage_results), 2)
        self.assertEqual(result.stage_results[-1].stage, ResearchStage.FAILED)
        self.assertEqual(result.errors[0].split(":", maxsplit=1)[0], "Alpha001MetricsEngine falhou")

    def test_continua_quando_etapa_nao_obrigatoria_falha(self) -> None:
        calls: list[str] = []
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep(
                    name="Alpha001Experiment",
                    order=1,
                    description="Experiment",
                    enabled=True,
                    required=True,
                ),
                ResearchExecutionStep(
                    name="Alpha001MetricsEngine",
                    order=2,
                    description="Metrics",
                    enabled=True,
                    required=False,
                ),
                ResearchExecutionStep(
                    name="Alpha001ProfitEngine",
                    order=3,
                    description="Profit",
                    enabled=True,
                    required=True,
                ),
            ),
        )
        runner = ResearchRunner(
            plan=plan,
            metrics_engine=_FailingCalculateSpy("metrics", calls),
            profit_engine=_CalculateSpy("profit", calls, self._profit()),
        )

        result = runner.run(_ExperimentSpy(calls))

        self.assertEqual(calls, ["experiment", "metrics", "profit"])
        self.assertEqual(result.status, ResearchStage.FAILED)
        self.assertEqual(len(result.stage_results), 3)

    def test_etapa_desabilitada_e_marcada_como_skipped(self) -> None:
        calls: list[str] = []
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep(
                    name="Alpha001Experiment",
                    order=1,
                    description="Experiment",
                    enabled=False,
                    required=True,
                ),
            ),
        )

        result = ResearchRunner(plan=plan).run(_ExperimentSpy(calls))

        self.assertEqual(calls, [])
        self.assertEqual(result.stage_results[0].stage, ResearchStage.SKIPPED)
        self.assertTrue(result.stage_results[0].success)

    def test_runner_nao_usa_threads_processos_asyncio_ou_camadas_operacionais(self) -> None:
        path = Path("research/research_runner.py")
        imports = imports_from(path)
        source = read_source(path)
        calls = calls_from(path)

        forbidden_imports = {
            "threading",
            "multiprocessing",
            "asyncio",
            "concurrent.futures",
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_fragments = (
            "async def",
            "await ",
            "Thread(",
            "Process(",
            "Pool(",
            "create_task",
            "gather(",
        )
        forbidden_calls = {
            "order_send",
            "execute_order",
            "send_order",
            "open",
            "write",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertEqual(
            [fragment for fragment in forbidden_fragments if fragment in source],
            [],
        )
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _metrics(self) -> Alpha001MetricsResult:
        return Alpha001MetricsResult(1, 1, 0, 0)

    def _profit(self) -> Alpha001ProfitResult:
        return Alpha001ProfitResult(10.0, 5.0, 5.0)

    def _drawdown(self) -> Alpha001DrawdownResult:
        return Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0)

    def _win_rate(self) -> Alpha001WinRateResult:
        return Alpha001WinRateResult(1, 0, 0, 1.0)

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
    """Experimento controlado para o runner."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def run(self) -> Alpha001ExperimentResult:
        self.calls.append("experiment")
        return Alpha001ExperimentResult(
            total_candles=1,
            total_signals=1,
            total_buy=1,
            total_sell=0,
            total_wait=0,
            execution_time_ms=1.0,
            signals=(),
        )


class _CalculateSpy:
    """Componente com calculate controlado."""

    def __init__(
        self,
        name: str,
        calls: list[str],
        result: object,
        expected_input: object | None = None,
    ) -> None:
        self.name = name
        self.calls = calls
        self.result = result
        self.expected_input = expected_input

    def calculate(self, value: object) -> object:
        if self.expected_input is not None:
            assert value is self.expected_input
        self.calls.append(self.name)
        return self.result


class _FailingCalculateSpy:
    """Componente que falha em calculate."""

    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def calculate(self, value: object) -> object:
        self.calls.append(self.name)
        raise RuntimeError("falha controlada")


class _ComparatorSpy:
    """Comparador controlado."""

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


class _ValidatorSpy:
    """Validador controlado."""

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


class _AdvisorSpy:
    """Advisor controlado."""

    def __init__(
        self,
        calls: list[str],
        result: Alpha001ResearchRecommendation,
        expected_input: Alpha001ResearchValidationResult,
    ) -> None:
        self.calls = calls
        self.result = result
        self.expected_input = expected_input

    def recommend(
        self,
        validation_result: Alpha001ResearchValidationResult,
    ) -> Alpha001ResearchRecommendation:
        assert validation_result is self.expected_input
        self.calls.append("advisor")
        return self.result


if __name__ == "__main__":
    unittest.main()
