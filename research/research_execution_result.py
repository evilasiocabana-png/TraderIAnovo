"""Resultado oficial de uma execucao completa do Research Pipeline."""

from dataclasses import dataclass
from datetime import datetime

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
from research.research_stage import ResearchStage, ResearchStageResult


@dataclass(frozen=True)
class ResearchExecutionResult:
    """Consolida os resultados de uma execucao completa de pesquisa."""

    experiment: Alpha001ExperimentResult
    metrics: Alpha001MetricsResult
    profit: Alpha001ProfitResult
    drawdown: Alpha001DrawdownResult
    win_rate: Alpha001WinRateResult
    profit_factor: Alpha001ProfitFactorResult
    expectancy: Alpha001ExpectancyResult
    benchmark: Alpha001BenchmarkResult
    research_report: Alpha001ResearchResult
    validation: Alpha001ResearchValidationResult
    recommendation: Alpha001ResearchRecommendation
    stage_results: tuple[ResearchStageResult, ...]
    started_at: datetime | None
    finished_at: datetime | None
    duration: float
    status: ResearchStage
    errors: tuple[str, ...]
