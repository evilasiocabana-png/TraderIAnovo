"""Testes do resultado oficial de execucao do Research Pipeline."""

from dataclasses import FrozenInstanceError, is_dataclass
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
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage, ResearchStageResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchExecutionResultTest(unittest.TestCase):
    """Valida consolidacao declarativa da execucao completa."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchExecutionResult))
        self.assertTrue(ResearchExecutionResult.__dataclass_params__.frozen)

    def test_agrega_todos_os_resultados_tipados(self) -> None:
        result = self._execution_result()

        self.assertIsInstance(result.experiment, Alpha001ExperimentResult)
        self.assertIsInstance(result.metrics, Alpha001MetricsResult)
        self.assertIsInstance(result.profit, Alpha001ProfitResult)
        self.assertIsInstance(result.drawdown, Alpha001DrawdownResult)
        self.assertIsInstance(result.win_rate, Alpha001WinRateResult)
        self.assertIsInstance(result.profit_factor, Alpha001ProfitFactorResult)
        self.assertIsInstance(result.expectancy, Alpha001ExpectancyResult)
        self.assertIsInstance(result.benchmark, Alpha001BenchmarkResult)
        self.assertIsInstance(result.research_report, Alpha001ResearchResult)
        self.assertIsInstance(result.validation, Alpha001ResearchValidationResult)
        self.assertIsInstance(result.recommendation, Alpha001ResearchRecommendation)
        self.assertIsInstance(result.stage_results[0], ResearchStageResult)
        self.assertEqual(result.status, ResearchStage.COMPLETED)

    def test_preserva_referencias_recebidas_sem_recalcular(self) -> None:
        experiment = self._experiment()
        metrics = self._metrics()
        profit = self._profit()
        drawdown = self._drawdown()
        win_rate = self._win_rate()
        profit_factor = self._profit_factor()
        expectancy = self._expectancy()
        research_report = self._research_report(
            metrics,
            profit,
            drawdown,
            win_rate,
            profit_factor,
            expectancy,
        )
        benchmark = self._benchmark(research_report)
        validation = self._validation()
        recommendation = self._recommendation()
        stage_results = (self._stage_result(),)

        result = ResearchExecutionResult(
            experiment=experiment,
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            benchmark=benchmark,
            research_report=research_report,
            validation=validation,
            recommendation=recommendation,
            stage_results=stage_results,
            started_at=None,
            finished_at=None,
            duration=0.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )

        self.assertIs(result.experiment, experiment)
        self.assertIs(result.metrics, metrics)
        self.assertIs(result.profit, profit)
        self.assertIs(result.drawdown, drawdown)
        self.assertIs(result.win_rate, win_rate)
        self.assertIs(result.profit_factor, profit_factor)
        self.assertIs(result.expectancy, expectancy)
        self.assertIs(result.benchmark, benchmark)
        self.assertIs(result.research_report, research_report)
        self.assertIs(result.validation, validation)
        self.assertIs(result.recommendation, recommendation)
        self.assertIs(result.stage_results, stage_results)

    def test_contem_metadados_da_execucao(self) -> None:
        started_at = datetime(2026, 6, 27, 20, 40, 0)
        finished_at = datetime(2026, 6, 27, 20, 40, 2)
        result = self._execution_result(
            started_at=started_at,
            finished_at=finished_at,
            duration=2.0,
            status=ResearchStage.FAILED,
            errors=("Erro controlado.",),
        )

        self.assertEqual(result.started_at, started_at)
        self.assertEqual(result.finished_at, finished_at)
        self.assertEqual(result.duration, 2.0)
        self.assertEqual(result.status, ResearchStage.FAILED)
        self.assertEqual(result.errors, ("Erro controlado.",))

    def test_resultado_e_imutavel(self) -> None:
        result = self._execution_result()

        with self.assertRaises(FrozenInstanceError):
            result.status = ResearchStage.FAILED

    def test_resultado_nao_executa_logica_nem_importa_camadas_operacionais(self) -> None:
        path = Path("research/research_execution_result.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "compare",
            "validate",
            "recommend",
            "open",
            "write",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_codigo_fonte_nao_realiza_calculos(self) -> None:
        source = read_source(Path("research/research_execution_result.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
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

    def _execution_result(
        self,
        *,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        duration: float = 0.0,
        status: ResearchStage = ResearchStage.COMPLETED,
        errors: tuple[str, ...] = (),
    ) -> ResearchExecutionResult:
        metrics = self._metrics()
        profit = self._profit()
        drawdown = self._drawdown()
        win_rate = self._win_rate()
        profit_factor = self._profit_factor()
        expectancy = self._expectancy()
        research_report = self._research_report(
            metrics,
            profit,
            drawdown,
            win_rate,
            profit_factor,
            expectancy,
        )
        return ResearchExecutionResult(
            experiment=self._experiment(),
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            benchmark=self._benchmark(research_report),
            research_report=research_report,
            validation=self._validation(),
            recommendation=self._recommendation(),
            stage_results=(self._stage_result(),),
            started_at=started_at,
            finished_at=finished_at,
            duration=duration,
            status=status,
            errors=errors,
        )

    def _experiment(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=1,
            total_signals=1,
            total_buy=1,
            total_sell=0,
            total_wait=0,
            execution_time_ms=1.0,
            signals=(),
        )

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

    def _research_report(
        self,
        metrics: Alpha001MetricsResult,
        profit: Alpha001ProfitResult,
        drawdown: Alpha001DrawdownResult,
        win_rate: Alpha001WinRateResult,
        profit_factor: Alpha001ProfitFactorResult,
        expectancy: Alpha001ExpectancyResult,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )

    def _benchmark(
        self,
        research_report: Alpha001ResearchResult,
    ) -> Alpha001BenchmarkResult:
        return Alpha001BenchmarkResult(
            total_results=1,
            best_overall=research_report,
            best_total_trades=research_report,
            best_net_profit=research_report,
            best_max_drawdown=research_report,
            best_profit_factor=research_report,
            best_win_rate=research_report,
            best_expectancy=research_report,
            ranking=(research_report,),
        )

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

    def _stage_result(self) -> ResearchStageResult:
        return ResearchStageResult(
            stage=ResearchStage.COMPLETED,
            started_at=None,
            finished_at=None,
            duration=0.0,
            success=True,
            message="Etapa concluida.",
        )


if __name__ == "__main__":
    unittest.main()
