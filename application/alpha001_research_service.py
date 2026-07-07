"""Servico de aplicacao para pesquisa consolidada da Alpha 001."""

from dataclasses import dataclass, field

from research.alpha001_drawdown_engine import Alpha001DrawdownEngine
from research.alpha001_expectancy_engine import Alpha001ExpectancyEngine
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsEngine
from research.alpha001_profit_engine import Alpha001ProfitEngine
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorEngine
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateEngine


@dataclass
class Alpha001ResearchService:
    """Orquestra engines de pesquisa da Alpha001 sem calcular metricas."""

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

    def run(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001ResearchResult:
        """Executa os engines na ordem oficial e agrega os resultados."""
        metrics = self.metrics_engine.calculate(experiment_result)
        profit = self.profit_engine.calculate(experiment_result)
        drawdown = self.drawdown_engine.calculate(experiment_result)
        win_rate = self.win_rate_engine.calculate(experiment_result)
        profit_factor = self.profit_factor_engine.calculate(profit)
        expectancy = self.expectancy_engine.calculate(experiment_result)
        return Alpha001ResearchResult(
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )
