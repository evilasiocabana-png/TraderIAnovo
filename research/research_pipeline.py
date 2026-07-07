"""Pipeline oficial de execucao do Research Lab."""

from dataclasses import dataclass, field
from typing import Iterable

from research.alpha001_benchmark_comparator import (
    Alpha001BenchmarkComparator,
    Alpha001BenchmarkResult,
)
from research.alpha001_drawdown_engine import Alpha001DrawdownEngine
from research.alpha001_expectancy_engine import Alpha001ExpectancyEngine
from research.alpha001_experiment import Alpha001Experiment, Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsEngine
from research.alpha001_profit_engine import Alpha001ProfitEngine
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorEngine
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


@dataclass(frozen=True)
class ResearchPipelineResult:
    """Resultado consolidado da orquestracao do Research Lab."""

    experiment: Alpha001ExperimentResult
    research: Alpha001ResearchResult
    benchmark: Alpha001BenchmarkResult
    validation: Alpha001ResearchValidationResult
    recommendation: Alpha001ResearchRecommendation


@dataclass
class ResearchPipeline:
    """Controla a sequencia oficial sem realizar calculos diretamente."""

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
        experiment: Alpha001Experiment,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchPipelineResult:
        """Executa a sequencia oficial de pesquisa Alpha 001."""
        experiment_result = experiment.run()
        metrics = self.metrics_engine.calculate(experiment_result)
        profit = self.profit_engine.calculate(experiment_result)
        drawdown = self.drawdown_engine.calculate(experiment_result)
        win_rate = self.win_rate_engine.calculate(experiment_result)
        profit_factor = self.profit_factor_engine.calculate(profit)
        expectancy = self.expectancy_engine.calculate(experiment_result)
        research_result = Alpha001ResearchResult(
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )
        benchmark_input = [*benchmark_results, research_result]
        benchmark = self.benchmark_comparator.compare(benchmark_input)
        validation = self.validator.validate(research_result)
        recommendation = self.advisor.recommend(validation)
        return ResearchPipelineResult(
            experiment=experiment_result,
            research=research_result,
            benchmark=benchmark,
            validation=validation,
            recommendation=recommendation,
        )

    def run_alpha002(
        self,
        experiment: object,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchPipelineResult:
        """Executa a Alpha002 reutilizando a infraestrutura existente."""
        return self.run(experiment, benchmark_results)
