"""Analise de performance por periodo da Alpha001."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from domain.contracts.backtest_result import BacktestResult


@dataclass(frozen=True)
class PeriodBacktestResult:
    """BacktestResult associado a uma data de referencia."""

    date: str
    backtest_result: BacktestResult


@dataclass(frozen=True)
class PeriodPerformanceMetrics:
    """Metricas consolidadas por periodo."""

    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float


@dataclass(frozen=True)
class PeriodPerformanceReport:
    """Relatorio de performance de um periodo."""

    period: str
    metrics: PeriodPerformanceMetrics


@dataclass(frozen=True)
class PeriodPerformanceAnalysis:
    """Analise consolidada de performance temporal."""

    period_type: str
    reports: list[PeriodPerformanceReport] = field(default_factory=list)
    best_period: str | None = None
    worst_period: str | None = None


@dataclass(frozen=True)
class PeriodPerformanceAnalyzer:
    """Analisa resultados existentes agrupados por periodo."""

    def analyze(
        self,
        backtest_results: Iterable[object],
        period: str,
    ) -> PeriodPerformanceAnalysis:
        """Consolida metricas por DAY, WEEK ou MONTH."""
        period_type = self._normalize_period(period)
        grouped = self._group_by_period(backtest_results, period_type)
        reports = [
            self._report(period_key, grouped[period_key])
            for period_key in sorted(grouped)
        ]
        return PeriodPerformanceAnalysis(
            period_type=period_type,
            reports=reports,
            best_period=self._best_period(reports),
            worst_period=self._worst_period(reports),
        )

    def _normalize_period(self, period: str) -> str:
        normalized = period.upper()
        if normalized not in {"DAY", "WEEK", "MONTH"}:
            raise ValueError(f"Periodo invalido: {period}")
        return normalized

    def _group_by_period(
        self,
        results: Iterable[object],
        period_type: str,
    ) -> dict[str, list[BacktestResult]]:
        grouped: dict[str, list[BacktestResult]] = {}
        for result in results:
            entry = self._normalize_result(result)
            key = self._period_key(entry.date, period_type)
            grouped.setdefault(key, []).append(entry.backtest_result)
        return grouped

    def _normalize_result(self, result: object) -> PeriodBacktestResult:
        if isinstance(result, PeriodBacktestResult):
            return result
        if isinstance(result, dict):
            return PeriodBacktestResult(
                date=str(result.get("date", result.get("datetime", ""))),
                backtest_result=result["backtest_result"],
            )
        if isinstance(result, tuple) and len(result) == 2:
            return PeriodBacktestResult(date=str(result[0]), backtest_result=result[1])
        return PeriodBacktestResult(
            date=str(getattr(result, "date", getattr(result, "datetime", ""))),
            backtest_result=getattr(result, "backtest_result"),
        )

    def _period_key(self, date_value: str, period_type: str) -> str:
        date = self._parse_date(date_value)
        if period_type == "DAY":
            return date.strftime("%Y-%m-%d")
        if period_type == "WEEK":
            year, week, _ = date.isocalendar()
            return f"{year}-W{week:02d}"
        return date.strftime("%Y-%m")

    def _parse_date(self, value: str) -> datetime:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"Data invalida: {value}")

    def _report(
        self,
        period_key: str,
        results: list[BacktestResult],
    ) -> PeriodPerformanceReport:
        return PeriodPerformanceReport(
            period=period_key,
            metrics=self._metrics(results),
        )

    def _metrics(
        self,
        results: list[BacktestResult],
    ) -> PeriodPerformanceMetrics:
        total_trades = sum(result.total_trades for result in results)
        return PeriodPerformanceMetrics(
            total_trades=total_trades,
            win_rate=self._weighted_win_rate(results, total_trades),
            profit_factor=self._average([result.profit_factor for result in results]),
            max_drawdown_points=max(result.drawdown for result in results),
            net_profit_points=sum(result.total_profit for result in results),
        )

    def _weighted_win_rate(
        self,
        results: list[BacktestResult],
        total_trades: int,
    ) -> float:
        if total_trades == 0:
            return 0.0
        weighted = sum(result.win_rate * result.total_trades for result in results)
        return weighted / total_trades

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _best_period(
        self,
        reports: list[PeriodPerformanceReport],
    ) -> str | None:
        if not reports:
            return None
        return max(reports, key=self._ranking_score).period

    def _worst_period(
        self,
        reports: list[PeriodPerformanceReport],
    ) -> str | None:
        if not reports:
            return None
        return min(reports, key=self._ranking_score).period

    def _ranking_score(self, report: PeriodPerformanceReport) -> tuple[float, ...]:
        metrics = report.metrics
        return (
            metrics.net_profit_points,
            metrics.profit_factor,
            metrics.win_rate,
            -metrics.max_drawdown_points,
            float(metrics.total_trades),
        )
