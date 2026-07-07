"""Analise de performance por regime de mercado."""

from dataclasses import dataclass, field
from typing import Iterable

from domain.contracts.backtest_result import BacktestResult


@dataclass(frozen=True)
class RegimeBacktestResult:
    """BacktestResult associado a um regime de mercado."""

    regime: str
    backtest_result: BacktestResult


@dataclass(frozen=True)
class RegimePerformanceMetrics:
    """Metricas consolidadas por regime."""

    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float


@dataclass(frozen=True)
class RegimePerformanceReport:
    """Relatorio de performance de um regime."""

    regime: str
    metrics: RegimePerformanceMetrics
    recommendation: str


@dataclass(frozen=True)
class RegimePerformanceAnalysis:
    """Analise consolidada de todos os regimes."""

    reports: list[RegimePerformanceReport] = field(default_factory=list)
    best_regime: str | None = None
    worst_regime: str | None = None


@dataclass(frozen=True)
class RegimePerformanceAnalyzer:
    """Analisa resultados existentes agrupados por regime."""

    def analyze(
        self,
        backtest_results: Iterable[object],
    ) -> RegimePerformanceAnalysis:
        """Consolida metricas por regime sem executar experimentos."""
        grouped = self._group_by_regime(backtest_results)
        reports = [
            self._report(regime, grouped[regime])
            for regime in self._ordered_regimes(grouped)
        ]
        return RegimePerformanceAnalysis(
            reports=reports,
            best_regime=self._best_regime(reports),
            worst_regime=self._worst_regime(reports),
        )

    def _group_by_regime(
        self,
        results: Iterable[object],
    ) -> dict[str, list[BacktestResult]]:
        grouped: dict[str, list[BacktestResult]] = {}
        for result in results:
            entry = self._normalize(result)
            grouped.setdefault(entry.regime, []).append(entry.backtest_result)
        return grouped

    def _normalize(self, result: object) -> RegimeBacktestResult:
        if isinstance(result, RegimeBacktestResult):
            return RegimeBacktestResult(
                regime=self._normalize_regime(result.regime),
                backtest_result=result.backtest_result,
            )
        if isinstance(result, dict):
            return self._from_dict(result)
        if isinstance(result, tuple) and len(result) == 2:
            return RegimeBacktestResult(
                regime=self._normalize_regime(str(result[0])),
                backtest_result=result[1],
            )
        return RegimeBacktestResult(
            regime=self._normalize_regime(str(getattr(result, "regime", "UNKNOWN"))),
            backtest_result=getattr(result, "backtest_result"),
        )

    def _from_dict(self, result: dict) -> RegimeBacktestResult:
        return RegimeBacktestResult(
            regime=self._normalize_regime(str(result.get("regime", "UNKNOWN"))),
            backtest_result=result["backtest_result"],
        )

    def _normalize_regime(self, regime: str) -> str:
        normalized = regime.upper()
        if normalized in self._known_regimes():
            return normalized
        return "UNKNOWN"

    def _known_regimes(self) -> tuple[str, ...]:
        return ("TREND", "RANGE", "BREAKOUT", "REVERSAL", "UNKNOWN")

    def _ordered_regimes(
        self,
        grouped: dict[str, list[BacktestResult]],
    ) -> list[str]:
        official = [regime for regime in self._known_regimes() if regime in grouped]
        extras = sorted(regime for regime in grouped if regime not in official)
        return official + extras

    def _report(
        self,
        regime: str,
        results: list[BacktestResult],
    ) -> RegimePerformanceReport:
        metrics = self._metrics(results)
        return RegimePerformanceReport(
            regime=regime,
            metrics=metrics,
            recommendation=self._recommendation(metrics),
        )

    def _metrics(
        self,
        results: list[BacktestResult],
    ) -> RegimePerformanceMetrics:
        total_trades = sum(result.total_trades for result in results)
        return RegimePerformanceMetrics(
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

    def _recommendation(self, metrics: RegimePerformanceMetrics) -> str:
        if metrics.total_trades == 0:
            return "INSUFFICIENT_DATA"
        if metrics.net_profit_points > 0 and metrics.profit_factor >= 1.2:
            return "FAVORABLE_REGIME"
        if metrics.net_profit_points < 0 or metrics.profit_factor < 1.0:
            return "AVOID_REGIME"
        return "NEUTRAL_REGIME"

    def _best_regime(
        self,
        reports: list[RegimePerformanceReport],
    ) -> str | None:
        if not reports:
            return None
        return max(reports, key=self._ranking_score).regime

    def _worst_regime(
        self,
        reports: list[RegimePerformanceReport],
    ) -> str | None:
        if not reports:
            return None
        return min(reports, key=self._ranking_score).regime

    def _ranking_score(self, report: RegimePerformanceReport) -> tuple[float, ...]:
        metrics = report.metrics
        return (
            metrics.net_profit_points,
            metrics.profit_factor,
            metrics.win_rate,
            -metrics.max_drawdown_points,
            float(metrics.total_trades),
        )
