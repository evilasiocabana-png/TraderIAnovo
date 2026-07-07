"""Comparador oficial de benchmarks de estrategias."""

from dataclasses import dataclass, field

from research.alpha001_experiment import Alpha001ExperimentResult
from research.strategy_benchmark import StrategyBenchmarkResult


@dataclass(frozen=True)
class BenchmarkComparison:
    """Resultado consolidado da comparacao de benchmarks."""

    best_strategy: str | None
    best_profit: float
    best_profit_factor: float
    best_drawdown: float
    best_win_rate: float
    ranking: list[StrategyBenchmarkResult] = field(default_factory=list)


@dataclass(frozen=True)
class Alpha001BenchmarkComparison:
    """Relatorio tipado da comparacao entre dois resultados Alpha 001."""

    left_label: str
    right_label: str
    best_label: str | None
    profit_factor_delta: float
    win_rate_delta: float
    drawdown_delta: float
    net_profit_delta: float
    total_trades_delta: int
    left_result: Alpha001ExperimentResult
    right_result: Alpha001ExperimentResult


@dataclass(frozen=True)
class BenchmarkComparator:
    """Compara benchmarks sem operar, otimizar ou usar IA."""

    def compare(
        self,
        benchmarks: list[StrategyBenchmarkResult],
    ) -> BenchmarkComparison:
        """Ordena benchmarks e retorna a melhor estrategia."""
        ranking = sorted(
            benchmarks,
            key=self._ranking_key,
            reverse=True,
        )
        if not ranking:
            return self._empty_comparison()
        best = ranking[0]
        return BenchmarkComparison(
            best_strategy=best.strategy_name,
            best_profit=best.net_profit_points,
            best_profit_factor=best.profit_factor,
            best_drawdown=best.max_drawdown_points,
            best_win_rate=best.win_rate,
            ranking=ranking,
        )

    def _ranking_key(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> tuple[float, float, float]:
        return (
            benchmark.net_profit_points,
            benchmark.profit_factor,
            benchmark.win_rate,
        )

    def _empty_comparison(self) -> BenchmarkComparison:
        return BenchmarkComparison(
            best_strategy=None,
            best_profit=0.0,
            best_profit_factor=0.0,
            best_drawdown=0.0,
            best_win_rate=0.0,
            ranking=[],
        )

    def compare_alpha001(
        self,
        left: Alpha001ExperimentResult,
        right: Alpha001ExperimentResult,
        left_label: str = "left",
        right_label: str = "right",
    ) -> Alpha001BenchmarkComparison:
        """Compara dois resultados Alpha001ExperimentResult."""
        best_label = self._best_alpha001_label(
            left,
            right,
            left_label,
            right_label,
        )
        return Alpha001BenchmarkComparison(
            left_label=left_label,
            right_label=right_label,
            best_label=best_label,
            profit_factor_delta=0.0,
            win_rate_delta=0.0,
            drawdown_delta=0.0,
            net_profit_delta=0.0,
            total_trades_delta=right.total_signals - left.total_signals,
            left_result=left,
            right_result=right,
        )

    def _best_alpha001_label(
        self,
        left: Alpha001ExperimentResult,
        right: Alpha001ExperimentResult,
        left_label: str,
        right_label: str,
    ) -> str | None:
        left_key = self._alpha001_ranking_key(left)
        right_key = self._alpha001_ranking_key(right)
        if left_key == right_key:
            return None
        if left_key > right_key:
            return left_label
        return right_label

    def _alpha001_ranking_key(
        self,
        result: Alpha001ExperimentResult,
    ) -> tuple[float, float, float, float, int]:
        return (
            0.0,
            0.0,
            0.0,
            0.0,
            result.total_signals,
        )
