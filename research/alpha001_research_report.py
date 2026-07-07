"""Agregador oficial de resultados de pesquisa da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_winrate_engine import Alpha001WinRateResult


@dataclass(frozen=True)
class Alpha001ResearchResult:
    """Resultado consolidado de pesquisa da Alpha 001.

    Este contrato apenas agrega resultados produzidos por engines anteriores.
    """

    metrics: Alpha001MetricsResult
    profit: Alpha001ProfitResult
    drawdown: Alpha001DrawdownResult
    win_rate: Alpha001WinRateResult
    profit_factor: Alpha001ProfitFactorResult
    expectancy: Alpha001ExpectancyResult
