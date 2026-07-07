"""Executor oficial do Research Pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Callable, Iterable

from research.alpha001_benchmark_comparator import (
    Alpha001BenchmarkComparator,
    Alpha001BenchmarkResult,
)
from research.alpha001_drawdown_engine import Alpha001DrawdownEngine
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyEngine
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsEngine
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitEngine
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorEngine
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import (
    Alpha001ResearchAdvisor,
    Alpha001ResearchRecommendation,
)
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import (
    Alpha001ResearchValidationResult,
    Alpha001ResearchValidator,
)
from research.alpha001_winrate_engine import Alpha001WinRateEngine
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.research_execution_plan import ResearchExecutionPlan
from research.research_execution_plan import ResearchExecutionStep
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from research.research_stage import ResearchStageResult


StepHandler = Callable[["_RunnerContext"], None]


@dataclass
class ResearchRunner:
    """Executa o plano de pesquisa em ordem sequencial."""

    plan: ResearchExecutionPlan
    metrics_engine: Alpha001MetricsEngine = field(
        default_factory=Alpha001MetricsEngine,
    )
    profit_engine: Alpha001ProfitEngine = field(
        default_factory=Alpha001ProfitEngine,
    )
    drawdown_engine: Alpha001DrawdownEngine = field(
        default_factory=Alpha001DrawdownEngine,
    )
    win_rate_engine: Alpha001WinRateEngine = field(
        default_factory=Alpha001WinRateEngine,
    )
    profit_factor_engine: Alpha001ProfitFactorEngine = field(
        default_factory=Alpha001ProfitFactorEngine,
    )
    expectancy_engine: Alpha001ExpectancyEngine = field(
        default_factory=Alpha001ExpectancyEngine,
    )
    benchmark_comparator: Alpha001BenchmarkComparator = field(
        default_factory=Alpha001BenchmarkComparator,
    )
    validator: Alpha001ResearchValidator = field(
        default_factory=lambda: Alpha001ResearchValidator(
            minimum_trades=30,
            minimum_profit_factor=1.2,
            maximum_drawdown=100.0,
            minimum_win_rate=0.4,
        ),
    )
    advisor: Alpha001ResearchAdvisor = field(
        default_factory=Alpha001ResearchAdvisor,
    )

    def run(
        self,
        experiment: Any,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchExecutionResult:
        """Executa o plano informado sem paralelismo."""
        started_at = datetime.now()
        started_counter = perf_counter()
        context = _RunnerContext(
            experiment_source=experiment,
            benchmark_results=tuple(benchmark_results),
        )
        stage_results: list[ResearchStageResult] = []
        errors: list[str] = []

        for step in sorted(self.plan.steps, key=lambda item: item.order):
            if not step.enabled:
                stage_results.append(self._skipped_result(step))
                continue

            stage_result = self._execute_step(step, context)
            stage_results.append(stage_result)
            if not stage_result.success:
                errors.append(stage_result.message)
                if step.required:
                    break

        finished_at = datetime.now()
        duration = perf_counter() - started_counter
        status = ResearchStage.FAILED if errors else ResearchStage.COMPLETED
        return self._execution_result(
            context=context,
            stage_results=tuple(stage_results),
            started_at=started_at,
            finished_at=finished_at,
            duration=duration,
            status=status,
            errors=tuple(errors),
        )

    def _execute_step(
        self,
        step: ResearchExecutionStep,
        context: "_RunnerContext",
    ) -> ResearchStageResult:
        started_at = datetime.now()
        started_counter = perf_counter()
        try:
            self._handlers()[step.name](context)
            return ResearchStageResult(
                stage=ResearchStage.COMPLETED,
                started_at=started_at,
                finished_at=datetime.now(),
                duration=perf_counter() - started_counter,
                success=True,
                message=f"{step.name} concluida.",
            )
        except Exception as exc:
            return ResearchStageResult(
                stage=ResearchStage.FAILED,
                started_at=started_at,
                finished_at=datetime.now(),
                duration=perf_counter() - started_counter,
                success=False,
                message=f"{step.name} falhou: {exc}",
            )

    def _handlers(self) -> dict[str, StepHandler]:
        return {
            "Alpha001Experiment": self._run_experiment,
            "Alpha002Experiment": self._run_experiment,
            "Alpha001MetricsEngine": self._run_metrics,
            "Alpha001ProfitEngine": self._run_profit,
            "Alpha001DrawdownEngine": self._run_drawdown,
            "Alpha001WinRateEngine": self._run_win_rate,
            "Alpha001ProfitFactorEngine": self._run_profit_factor,
            "Alpha001ExpectancyEngine": self._run_expectancy,
            "Alpha001BenchmarkComparator": self._run_benchmark,
            "Alpha001ResearchReport": self._run_research_report,
            "Alpha001ResearchValidator": self._run_validation,
            "Alpha001ResearchAdvisor": self._run_recommendation,
        }

    def _run_experiment(self, context: "_RunnerContext") -> None:
        context.experiment = context.experiment_source.run()

    def _run_metrics(self, context: "_RunnerContext") -> None:
        context.metrics = self.metrics_engine.calculate(
            self._require_experiment(context),
        )

    def _run_profit(self, context: "_RunnerContext") -> None:
        context.profit = self.profit_engine.calculate(
            self._require_experiment(context),
        )

    def _run_drawdown(self, context: "_RunnerContext") -> None:
        context.drawdown = self.drawdown_engine.calculate(
            self._require_experiment(context),
        )

    def _run_win_rate(self, context: "_RunnerContext") -> None:
        context.win_rate = self.win_rate_engine.calculate(
            self._require_experiment(context),
        )

    def _run_profit_factor(self, context: "_RunnerContext") -> None:
        context.profit_factor = self.profit_factor_engine.calculate(
            self._require_profit(context),
        )

    def _run_expectancy(self, context: "_RunnerContext") -> None:
        context.expectancy = self.expectancy_engine.calculate(
            self._require_experiment(context),
        )

    def _run_benchmark(self, context: "_RunnerContext") -> None:
        research_report = self._current_research_report(context)
        context.benchmark = self.benchmark_comparator.compare(
            [*context.benchmark_results, research_report],
        )

    def _run_research_report(self, context: "_RunnerContext") -> None:
        context.research_report = self._current_research_report(context)

    def _run_validation(self, context: "_RunnerContext") -> None:
        context.validation = self.validator.validate(
            self._require_research_report(context),
        )

    def _run_recommendation(self, context: "_RunnerContext") -> None:
        context.recommendation = self.advisor.recommend(
            self._require_validation(context),
        )

    def _current_research_report(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=self._require_metrics(context),
            profit=self._require_profit(context),
            drawdown=self._require_drawdown(context),
            win_rate=self._require_win_rate(context),
            profit_factor=self._require_profit_factor(context),
            expectancy=self._require_expectancy(context),
        )

    def _execution_result(
        self,
        context: "_RunnerContext",
        stage_results: tuple[ResearchStageResult, ...],
        started_at: datetime,
        finished_at: datetime,
        duration: float,
        status: ResearchStage,
        errors: tuple[str, ...],
    ) -> ResearchExecutionResult:
        research_report = context.research_report or self._empty_research_report()
        return ResearchExecutionResult(
            experiment=context.experiment or self._empty_experiment(),
            metrics=context.metrics or research_report.metrics,
            profit=context.profit or research_report.profit,
            drawdown=context.drawdown or research_report.drawdown,
            win_rate=context.win_rate or research_report.win_rate,
            profit_factor=context.profit_factor or research_report.profit_factor,
            expectancy=context.expectancy or research_report.expectancy,
            benchmark=context.benchmark or self._empty_benchmark(research_report),
            research_report=research_report,
            validation=context.validation or self._empty_validation(),
            recommendation=context.recommendation or self._empty_recommendation(),
            stage_results=stage_results,
            started_at=started_at,
            finished_at=finished_at,
            duration=duration,
            status=status,
            errors=errors,
        )

    def _skipped_result(self, step: ResearchExecutionStep) -> ResearchStageResult:
        return ResearchStageResult(
            stage=ResearchStage.SKIPPED,
            started_at=None,
            finished_at=None,
            duration=0.0,
            success=True,
            message=f"{step.name} ignorada.",
        )

    def _require_experiment(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ExperimentResult:
        if context.experiment is None:
            raise RuntimeError("Alpha001ExperimentResult indisponivel")
        return context.experiment

    def _require_metrics(
        self,
        context: "_RunnerContext",
    ) -> Alpha001MetricsResult:
        if context.metrics is None:
            raise RuntimeError("Alpha001MetricsResult indisponivel")
        return context.metrics

    def _require_profit(self, context: "_RunnerContext") -> Alpha001ProfitResult:
        if context.profit is None:
            raise RuntimeError("Alpha001ProfitResult indisponivel")
        return context.profit

    def _require_drawdown(
        self,
        context: "_RunnerContext",
    ) -> Alpha001DrawdownResult:
        if context.drawdown is None:
            raise RuntimeError("Alpha001DrawdownResult indisponivel")
        return context.drawdown

    def _require_win_rate(
        self,
        context: "_RunnerContext",
    ) -> Alpha001WinRateResult:
        if context.win_rate is None:
            raise RuntimeError("Alpha001WinRateResult indisponivel")
        return context.win_rate

    def _require_profit_factor(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ProfitFactorResult:
        if context.profit_factor is None:
            raise RuntimeError("Alpha001ProfitFactorResult indisponivel")
        return context.profit_factor

    def _require_expectancy(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ExpectancyResult:
        if context.expectancy is None:
            raise RuntimeError("Alpha001ExpectancyResult indisponivel")
        return context.expectancy

    def _require_research_report(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ResearchResult:
        if context.research_report is None:
            raise RuntimeError("Alpha001ResearchResult indisponivel")
        return context.research_report

    def _require_validation(
        self,
        context: "_RunnerContext",
    ) -> Alpha001ResearchValidationResult:
        if context.validation is None:
            raise RuntimeError("Alpha001ResearchValidationResult indisponivel")
        return context.validation

    def _empty_experiment(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=0,
            total_signals=0,
            total_buy=0,
            total_sell=0,
            total_wait=0,
            execution_time_ms=0.0,
            signals=(),
        )

    def _empty_research_report(self) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(0, 0, 0, 0),
            profit=Alpha001ProfitResult(0.0, 0.0, 0.0),
            drawdown=Alpha001DrawdownResult((0.0,), 0.0, 0.0),
            win_rate=Alpha001WinRateResult(0, 0, 0, 0.0),
            profit_factor=Alpha001ProfitFactorResult(0.0),
            expectancy=Alpha001ExpectancyResult(0.0, 0.0, 0.0, 0.0),
        )

    def _empty_benchmark(
        self,
        research_report: Alpha001ResearchResult,
    ) -> Alpha001BenchmarkResult:
        return Alpha001BenchmarkResult(
            total_results=0,
            best_overall=None,
            best_total_trades=None,
            best_net_profit=None,
            best_max_drawdown=None,
            best_profit_factor=None,
            best_win_rate=None,
            best_expectancy=None,
            ranking=(),
        )

    def _empty_validation(self) -> Alpha001ResearchValidationResult:
        return Alpha001ResearchValidationResult(
            approved=False,
            status="NOT_EXECUTED",
            reasons=("Validacao nao executada.",),
            minimum_trades=0,
            minimum_profit_factor=0.0,
            maximum_drawdown=0.0,
            minimum_win_rate=0.0,
            real_trading_authorized=False,
        )

    def _empty_recommendation(self) -> Alpha001ResearchRecommendation:
        return Alpha001ResearchRecommendation(
            recommendation="NOT_EXECUTED",
            status="NOT_EXECUTED",
            reasons=("Advisor nao executado.",),
            real_trading_authorized=False,
        )


@dataclass
class _RunnerContext:
    """Estado interno mutavel da execucao sequencial."""

    experiment_source: Any
    benchmark_results: tuple[Alpha001ResearchResult, ...]
    experiment: Alpha001ExperimentResult | None = None
    metrics: Alpha001MetricsResult | None = None
    profit: Alpha001ProfitResult | None = None
    drawdown: Alpha001DrawdownResult | None = None
    win_rate: Alpha001WinRateResult | None = None
    profit_factor: Alpha001ProfitFactorResult | None = None
    expectancy: Alpha001ExpectancyResult | None = None
    benchmark: Alpha001BenchmarkResult | None = None
    research_report: Alpha001ResearchResult | None = None
    validation: Alpha001ResearchValidationResult | None = None
    recommendation: Alpha001ResearchRecommendation | None = None
