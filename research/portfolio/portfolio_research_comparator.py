"""Comparador consolidado de pesquisas de multiplas Alphas."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class PortfolioResearchComparison:
    """Snapshot comparavel de uma Alpha pesquisada."""

    alpha_id: str
    total_trades: int
    net_profit: float
    max_drawdown: float
    profit_factor: float
    expectancy: float
    win_rate: float


@dataclass(frozen=True)
class PortfolioComparisonResult:
    """Resultado consolidado da comparacao de portfolio."""

    total_results: int
    comparisons: tuple[PortfolioResearchComparison, ...]


@dataclass(frozen=True)
class PortfolioResearchComparator:
    """Consolida metricas ja calculadas sem ordenar resultados."""

    def compare(
        self,
        results: Iterable[Alpha001ResearchResult],
    ) -> PortfolioComparisonResult:
        """Retorna comparacao declarativa na ordem recebida."""
        comparisons = tuple(
            self._comparison(result)
            for result in results
        )
        return PortfolioComparisonResult(
            total_results=len(comparisons),
            comparisons=comparisons,
        )

    def _comparison(
        self,
        result: Alpha001ResearchResult,
    ) -> PortfolioResearchComparison:
        return PortfolioResearchComparison(
            alpha_id=self._alpha_id(result),
            total_trades=result.metrics.total_trades,
            net_profit=result.profit.net_profit_points,
            max_drawdown=result.drawdown.max_drawdown_points,
            profit_factor=result.profit_factor.profit_factor,
            expectancy=result.expectancy.expectancy,
            win_rate=result.win_rate.win_rate,
        )

    def _alpha_id(self, result: Alpha001ResearchResult) -> str:
        for attribute in ("alpha_id", "alpha_name", "alpha"):
            value = getattr(result, attribute, None)
            if value:
                return str(value)
        return "Alpha001"
