"""Analyzer oficial dos resultados Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass

from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult


@dataclass(frozen=True)
class MonteCarloAnalysisResult:
    """Resultado analitico da validacao Monte Carlo."""

    average_return: float
    worst_case_return: float
    best_case_return: float
    expected_drawdown: float
    robustness_score: float


@dataclass(frozen=True)
class MonteCarloAnalyzer:
    """Analisa resultados Monte Carlo sem recalcular metricas das Alphas."""

    def analyze(
        self,
        result: MonteCarloResult,
    ) -> MonteCarloAnalysisResult:
        """Consolida estatisticas derivadas das simulacoes Monte Carlo."""
        simulated_returns = result.simulated_returns
        simulated_drawdowns = result.simulated_drawdowns
        average_return = self._average(simulated_returns)
        worst_case_return = min(simulated_returns) if simulated_returns else 0.0
        best_case_return = max(simulated_returns) if simulated_returns else 0.0
        expected_drawdown = self._average(simulated_drawdowns)
        robustness_score = self._robustness_score(
            average_return,
            worst_case_return,
            best_case_return,
            expected_drawdown,
            len(simulated_returns),
        )
        return MonteCarloAnalysisResult(
            average_return=average_return,
            worst_case_return=worst_case_return,
            best_case_return=best_case_return,
            expected_drawdown=expected_drawdown,
            robustness_score=robustness_score,
        )

    def _robustness_score(
        self,
        average_return: float,
        worst_case_return: float,
        best_case_return: float,
        expected_drawdown: float,
        total_simulations: int,
    ) -> float:
        if total_simulations <= 0:
            return 0.0
        scale = (
            abs(best_case_return)
            + abs(worst_case_return)
            + expected_drawdown
        )
        if scale <= 0.0:
            return 0.0
        positive_return_score = self._clamp(max(average_return, 0.0) / scale)
        drawdown_score = self._clamp(1.0 - (expected_drawdown / scale))
        downside_score = self._clamp(1.0 - (abs(min(worst_case_return, 0.0)) / scale))
        return self._average(
            (
                positive_return_score,
                drawdown_score,
                downside_score,
            )
        )

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
