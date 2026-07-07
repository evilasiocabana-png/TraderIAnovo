"""Comparacao estatistica entre estrategias pesquisadas."""

from dataclasses import dataclass, field
from typing import Iterable

from domain.contracts.backtest_result import BacktestResult


@dataclass(frozen=True)
class StrategyComparisonEntry:
    """Resultado normalizado de uma estrategia para comparacao."""

    strategy_name: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float
    validation_status: str = "UNKNOWN"


@dataclass(frozen=True)
class StrategyMetricDifference:
    """Diferenca consolidada de uma metrica entre estrategias."""

    metric_name: str
    best_value: float
    worst_value: float
    difference: float


@dataclass(frozen=True)
class StrategyComparisonResult:
    """Resultado consolidado da comparacao entre estrategias."""

    ranking: list[StrategyComparisonEntry] = field(default_factory=list)
    winning_strategy: str | None = None
    metric_differences: list[StrategyMetricDifference] = field(
        default_factory=list,
    )
    summary: str = "Nenhum resultado disponivel para comparacao."


@dataclass(frozen=True)
class StrategyComparator:
    """Compara resultados existentes sem executar novos experimentos."""

    def compare(
        self,
        results: Iterable[object],
    ) -> StrategyComparisonResult:
        """Compara duas ou mais estrategias ja avaliadas."""
        entries = self._normalize_many(results)
        if len(entries) < 2:
            return self._insufficient_result(entries)
        ranking = sorted(entries, key=self._ranking_key)
        return StrategyComparisonResult(
            ranking=ranking,
            winning_strategy=ranking[0].strategy_name,
            metric_differences=self._metric_differences(ranking),
            summary=self._summary(ranking),
        )

    def _normalize_many(
        self,
        results: Iterable[object],
    ) -> list[StrategyComparisonEntry]:
        entries = []
        for index, result in enumerate(results, start=1):
            entries.append(self._normalize(result, index))
        return entries

    def _normalize(
        self,
        result: object,
        index: int,
    ) -> StrategyComparisonEntry:
        if isinstance(result, StrategyComparisonEntry):
            return result
        if isinstance(result, BacktestResult):
            return self._from_backtest_result(result, index)
        if isinstance(result, dict):
            return self._from_dict(result, index)
        return self._from_object(result, index)

    def _from_backtest_result(
        self,
        result: BacktestResult,
        index: int,
    ) -> StrategyComparisonEntry:
        return StrategyComparisonEntry(
            strategy_name=f"strategy_{index}",
            total_trades=result.total_trades,
            win_rate=float(result.win_rate),
            profit_factor=float(result.profit_factor),
            max_drawdown_points=float(result.drawdown),
            net_profit_points=float(result.total_profit),
        )

    def _from_dict(
        self,
        result: dict,
        index: int,
    ) -> StrategyComparisonEntry:
        backtest = result.get("backtest_result")
        if isinstance(backtest, BacktestResult):
            return self._from_backtest_dict(result, backtest, index)
        return StrategyComparisonEntry(
            strategy_name=str(result.get("strategy_name", f"strategy_{index}")),
            total_trades=int(result.get("total_trades", 0)),
            win_rate=float(result.get("win_rate", 0.0)),
            profit_factor=float(result.get("profit_factor", 0.0)),
            max_drawdown_points=float(result.get("max_drawdown_points", 0.0)),
            net_profit_points=float(result.get("net_profit_points", 0.0)),
            validation_status=str(result.get("validation_status", "UNKNOWN")),
        )

    def _from_backtest_dict(
        self,
        result: dict,
        backtest: BacktestResult,
        index: int,
    ) -> StrategyComparisonEntry:
        entry = self._from_backtest_result(backtest, index)
        return StrategyComparisonEntry(
            strategy_name=str(result.get("strategy_name", entry.strategy_name)),
            total_trades=entry.total_trades,
            win_rate=entry.win_rate,
            profit_factor=entry.profit_factor,
            max_drawdown_points=entry.max_drawdown_points,
            net_profit_points=entry.net_profit_points,
            validation_status=str(result.get("validation_status", "UNKNOWN")),
        )

    def _from_object(
        self,
        result: object,
        index: int,
    ) -> StrategyComparisonEntry:
        return StrategyComparisonEntry(
            strategy_name=str(getattr(result, "strategy_name", f"strategy_{index}")),
            total_trades=int(getattr(result, "total_trades", 0)),
            win_rate=float(getattr(result, "win_rate", 0.0)),
            profit_factor=float(getattr(result, "profit_factor", 0.0)),
            max_drawdown_points=float(
                getattr(result, "max_drawdown_points", 0.0),
            ),
            net_profit_points=float(getattr(result, "net_profit_points", 0.0)),
            validation_status=str(getattr(result, "validation_status", "UNKNOWN")),
        )

    def _ranking_key(
        self,
        entry: StrategyComparisonEntry,
    ) -> tuple[bool, float, float, float, float, int]:
        return (
            entry.validation_status != "APPROVED",
            -entry.net_profit_points,
            -entry.profit_factor,
            -entry.win_rate,
            entry.max_drawdown_points,
            -entry.total_trades,
        )

    def _metric_differences(
        self,
        ranking: list[StrategyComparisonEntry],
    ) -> list[StrategyMetricDifference]:
        return [
            self._difference("total_trades", ranking),
            self._difference("win_rate", ranking),
            self._difference("profit_factor", ranking),
            self._difference("max_drawdown_points", ranking, lower_is_better=True),
            self._difference("net_profit_points", ranking),
        ]

    def _difference(
        self,
        metric_name: str,
        ranking: list[StrategyComparisonEntry],
        lower_is_better: bool = False,
    ) -> StrategyMetricDifference:
        values = [float(getattr(entry, metric_name)) for entry in ranking]
        best = min(values) if lower_is_better else max(values)
        worst = max(values) if lower_is_better else min(values)
        return StrategyMetricDifference(metric_name, best, worst, abs(best - worst))

    def _summary(self, ranking: list[StrategyComparisonEntry]) -> str:
        winner = ranking[0]
        return (
            f"Estrategia vencedora: {winner.strategy_name}. "
            f"Net points: {winner.net_profit_points:.2f}. "
            f"Profit factor: {winner.profit_factor:.2f}."
        )

    def _insufficient_result(
        self,
        entries: list[StrategyComparisonEntry],
    ) -> StrategyComparisonResult:
        return StrategyComparisonResult(
            ranking=entries,
            winning_strategy=entries[0].strategy_name if entries else None,
            metric_differences=[],
            summary="Comparacao exige resultados de duas ou mais estrategias.",
        )
