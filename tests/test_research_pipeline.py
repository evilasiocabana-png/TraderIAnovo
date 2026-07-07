"""Testes do pipeline oficial do Research Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
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
from research.research_pipeline import ResearchPipeline, ResearchPipelineResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchPipelineTest(unittest.TestCase):
    """Valida orquestracao oficial do Research Lab."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchPipelineResult))
        self.assertTrue(ResearchPipelineResult.__dataclass_params__.frozen)

    def test_run_retorna_resultado_consolidado_tipado(self) -> None:
        result = ResearchPipeline().run(_EmptyExperiment())

        self.assertIsInstance(result, ResearchPipelineResult)
        self.assertIsInstance(result.experiment, Alpha001ExperimentResult)
        self.assertIsInstance(result.research, Alpha001ResearchResult)
        self.assertIsInstance(result.benchmark, Alpha001BenchmarkResult)
        self.assertIsInstance(result.validation, Alpha001ResearchValidationResult)
        self.assertIsInstance(result.recommendation, Alpha001ResearchRecommendation)

    def test_executa_componentes_na_ordem_oficial(self) -> None:
        calls: list[str] = []
        experiment_result = self._experiment_result()
        metrics = Alpha001MetricsResult(1, 1, 0, 0)
        profit = Alpha001ProfitResult(10.0, 5.0, 5.0)
        drawdown = Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0)
        win_rate = Alpha001WinRateResult(1, 0, 0, 1.0)
        profit_factor = Alpha001ProfitFactorResult(2.0)
        expectancy = Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0)
        validation = Alpha001ResearchValidationResult(
            approved=True,
            status="APPROVED",
            reasons=("ok",),
            minimum_trades=1,
            minimum_profit_factor=1.0,
            maximum_drawdown=10.0,
            minimum_win_rate=0.1,
            real_trading_authorized=False,
        )
        recommendation = Alpha001ResearchRecommendation(
            recommendation="APPROVED_FOR_MORE_RESEARCH",
            status="APPROVED",
            reasons=("ok",),
            real_trading_authorized=False,
        )
        pipeline = ResearchPipeline(
            metrics_engine=_SpyCalculate("metrics", calls, metrics),
            profit_engine=_SpyCalculate("profit", calls, profit),
            drawdown_engine=_SpyCalculate("drawdown", calls, drawdown),
            win_rate_engine=_SpyCalculate("win_rate", calls, win_rate),
            profit_factor_engine=_SpyCalculate(
                "profit_factor",
                calls,
                profit_factor,
                expected_input=profit,
            ),
            expectancy_engine=_SpyCalculate("expectancy", calls, expectancy),
            benchmark_comparator=_SpyComparator(calls),
            validator=_SpyValidator(calls, validation),
            advisor=_SpyAdvisor(calls, recommendation, validation),
        )

        result = pipeline.run(_SpyExperiment(calls, experiment_result))

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
        self.assertIs(result.experiment, experiment_result)
        self.assertEqual(result.research.metrics, metrics)
        self.assertEqual(result.research.profit, profit)
        self.assertEqual(result.research.drawdown, drawdown)
        self.assertEqual(result.research.win_rate, win_rate)
        self.assertEqual(result.research.profit_factor, profit_factor)
        self.assertEqual(result.research.expectancy, expectancy)
        self.assertIs(result.validation, validation)
        self.assertIs(result.recommendation, recommendation)

    def test_benchmark_recebe_resultados_anteriores_e_atual(self) -> None:
        comparator = _SpyComparator([])
        previous = self._research_result()
        pipeline = ResearchPipeline(benchmark_comparator=comparator)

        result = pipeline.run(_EmptyExperiment(), benchmark_results=(previous,))

        self.assertEqual(comparator.total_received, 2)
        self.assertIs(comparator.received[0], previous)
        self.assertIs(comparator.received[1], result.research)

    def test_resultado_e_imutavel(self) -> None:
        result = ResearchPipeline().run(_EmptyExperiment())

        with self.assertRaises(FrozenInstanceError):
            result.research = self._research_result()

    def test_pipeline_nao_recalcula_metricas_diretamente(self) -> None:
        source = read_source(Path("research/research_pipeline.py"))
        forbidden_fragments = (
            "Alpha001MetricsResult(",
            "Alpha001ProfitResult(",
            "Alpha001DrawdownResult(",
            "Alpha001WinRateResult(",
            "Alpha001ProfitFactorResult(",
            "Alpha001ExpectancyResult(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_pipeline_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/research_pipeline.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "write",
            "order_send",
            "execute_order",
            "send_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _experiment_result(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=1,
            total_signals=1,
            total_buy=1,
            total_sell=0,
            total_wait=0,
            execution_time_ms=1.0,
            signals=(),
        )

    def _research_result(self) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(1, 1, 0, 0),
            profit=Alpha001ProfitResult(10.0, 5.0, 5.0),
            drawdown=Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0),
            win_rate=Alpha001WinRateResult(1, 0, 0, 1.0),
            profit_factor=Alpha001ProfitFactorResult(2.0),
            expectancy=Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0),
        )


class _EmptyExperiment:
    """Experimento minimo para exercitar o pipeline real."""

    def run(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=0,
            total_signals=0,
            total_buy=0,
            total_sell=0,
            total_wait=0,
            execution_time_ms=0.0,
            signals=(),
        )


class _SpyExperiment:
    """Experimento controlado para validar ordem de execucao."""

    def __init__(
        self,
        calls: list[str],
        result: Alpha001ExperimentResult,
    ) -> None:
        self.calls = calls
        self.result = result

    def run(self) -> Alpha001ExperimentResult:
        self.calls.append("experiment")
        return self.result


class _SpyCalculate:
    """Componente com metodo calculate e entrada esperada opcional."""

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


class _SpyComparator:
    """Comparador controlado para validar entrada do benchmark."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.received: list[Alpha001ResearchResult] = []
        self.total_received = 0

    def compare(
        self,
        results: list[Alpha001ResearchResult],
    ) -> Alpha001BenchmarkResult:
        self.calls.append("benchmark")
        self.received = results
        self.total_received = len(results)
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
    """Validador controlado para validar ordem e entrada."""

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
    """Advisor controlado para validar ordem e entrada."""

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
