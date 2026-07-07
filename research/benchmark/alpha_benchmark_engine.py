"""Engine de benchmark entre Alphas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.research_execution_result import ResearchExecutionResult


@dataclass(frozen=True)
class AlphaBenchmarkComparison:
    """Snapshot comparavel de uma execucao de Alpha."""

    alpha_id: str
    experiment_id: str
    net_profit: float
    max_drawdown: float
    profit_factor: float
    win_rate: float
    expectancy: float
    robustness: float
    reproducibility: float


@dataclass(frozen=True)
class AlphaBenchmarkResult:
    """Resultado consolidado do benchmark entre Alphas."""

    profile: AlphaBenchmarkProfile
    total_results: int
    comparisons: tuple[AlphaBenchmarkComparison, ...]
    best_net_profit: AlphaBenchmarkComparison | None
    best_max_drawdown: AlphaBenchmarkComparison | None
    best_profit_factor: AlphaBenchmarkComparison | None
    best_win_rate: AlphaBenchmarkComparison | None
    best_expectancy: AlphaBenchmarkComparison | None
    best_robustness: AlphaBenchmarkComparison | None
    best_reproducibility: AlphaBenchmarkComparison | None


@dataclass(frozen=True)
class AlphaBenchmarkEngine:
    """Compara resultados existentes sem recalcular metricas."""

    def compare(
        self,
        profile: AlphaBenchmarkProfile,
        results: Iterable[ResearchExecutionResult],
    ) -> AlphaBenchmarkResult:
        """Retorna benchmark consolidado para as execucoes recebidas."""
        comparisons = tuple(
            self._comparison(profile, index, result)
            for index, result in enumerate(results)
        )
        if not comparisons:
            return AlphaBenchmarkResult(
                profile=profile,
                total_results=0,
                comparisons=(),
                best_net_profit=None,
                best_max_drawdown=None,
                best_profit_factor=None,
                best_win_rate=None,
                best_expectancy=None,
                best_robustness=None,
                best_reproducibility=None,
            )

        return AlphaBenchmarkResult(
            profile=profile,
            total_results=len(comparisons),
            comparisons=comparisons,
            best_net_profit=max(comparisons, key=lambda item: item.net_profit),
            best_max_drawdown=min(comparisons, key=lambda item: item.max_drawdown),
            best_profit_factor=max(comparisons, key=lambda item: item.profit_factor),
            best_win_rate=max(comparisons, key=lambda item: item.win_rate),
            best_expectancy=max(comparisons, key=lambda item: item.expectancy),
            best_robustness=max(comparisons, key=lambda item: item.robustness),
            best_reproducibility=max(
                comparisons,
                key=lambda item: item.reproducibility,
            ),
        )

    def _comparison(
        self,
        profile: AlphaBenchmarkProfile,
        index: int,
        result: ResearchExecutionResult,
    ) -> AlphaBenchmarkComparison:
        return AlphaBenchmarkComparison(
            alpha_id=self._alpha_id(profile, index),
            experiment_id=self._experiment_id(profile, index),
            net_profit=result.profit.net_profit_points,
            max_drawdown=result.drawdown.max_drawdown_points,
            profit_factor=result.profit_factor.profit_factor,
            win_rate=result.win_rate.win_rate,
            expectancy=result.expectancy.expectancy,
            robustness=self._score(result, "robustness_score"),
            reproducibility=self._score(result, "reproducibility_score"),
        )

    def _alpha_id(
        self,
        profile: AlphaBenchmarkProfile,
        index: int,
    ) -> str:
        if index == 0:
            return profile.alpha_a
        if index == 1:
            return profile.alpha_b
        return f"Alpha{index + 1}"

    def _experiment_id(
        self,
        profile: AlphaBenchmarkProfile,
        index: int,
    ) -> str:
        if index < len(profile.experiment_ids):
            return profile.experiment_ids[index]
        return ""

    def _score(
        self,
        result: ResearchExecutionResult,
        attribute: str,
    ) -> float:
        value = getattr(result, attribute, None)
        if value is None:
            value = getattr(result.research_report, attribute, 0.0)
        if not isinstance(value, (int, float)):
            return 0.0
        return float(value)
