"""Comparador de resultados agregados de pesquisa da Alpha 001."""

from dataclasses import dataclass, field

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001BenchmarkResult:
    """Resultado tipado da comparacao de pesquisas Alpha 001."""

    total_results: int
    best_overall: Alpha001ResearchResult | None
    best_total_trades: Alpha001ResearchResult | None
    best_net_profit: Alpha001ResearchResult | None
    best_max_drawdown: Alpha001ResearchResult | None
    best_profit_factor: Alpha001ResearchResult | None
    best_win_rate: Alpha001ResearchResult | None
    best_expectancy: Alpha001ResearchResult | None
    ranking: tuple[Alpha001ResearchResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Alpha001BenchmarkComparator:
    """Compara pesquisas Alpha 001 sem recalcular metricas."""

    def compare(
        self,
        results: list[Alpha001ResearchResult],
    ) -> Alpha001BenchmarkResult:
        """Retorna ranking e melhores resultados por metrica ja calculada."""
        ranking = tuple(
            sorted(
                results,
                key=self._ranking_key,
                reverse=True,
            )
        )
        if not ranking:
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

        return Alpha001BenchmarkResult(
            total_results=len(results),
            best_overall=ranking[0],
            best_total_trades=max(results, key=self._total_trades),
            best_net_profit=max(results, key=self._net_profit),
            best_max_drawdown=min(results, key=self._max_drawdown),
            best_profit_factor=max(results, key=self._profit_factor),
            best_win_rate=max(results, key=self._win_rate),
            best_expectancy=max(results, key=self._expectancy),
            ranking=ranking,
        )

    def _ranking_key(
        self,
        result: Alpha001ResearchResult,
    ) -> tuple[float, float, float, float, int, float]:
        return (
            self._net_profit(result),
            self._profit_factor(result),
            self._win_rate(result),
            self._expectancy(result),
            self._total_trades(result),
            -self._max_drawdown(result),
        )

    def _total_trades(self, result: Alpha001ResearchResult) -> int:
        return result.metrics.total_trades

    def _net_profit(self, result: Alpha001ResearchResult) -> float:
        return result.profit.net_profit_points

    def _max_drawdown(self, result: Alpha001ResearchResult) -> float:
        return result.drawdown.max_drawdown_points

    def _profit_factor(self, result: Alpha001ResearchResult) -> float:
        return result.profit_factor.profit_factor

    def _win_rate(self, result: Alpha001ResearchResult) -> float:
        return result.win_rate.win_rate

    def _expectancy(self, result: Alpha001ResearchResult) -> float:
        return result.expectancy.expectancy
