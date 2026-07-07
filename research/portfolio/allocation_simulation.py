"""Simulador teorico de alocacao de portfolio."""

from __future__ import annotations

from dataclasses import dataclass
import math

from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.research_execution_result import ResearchExecutionResult


@dataclass(frozen=True)
class AllocationSimulationResult:
    """Resultado da simulacao teorica de alocacao."""

    portfolio_equity_curve: tuple[float, ...]
    portfolio_return: float
    portfolio_drawdown: float
    portfolio_volatility: float


@dataclass(frozen=True)
class AllocationSimulation:
    """Simula alocacao usando resultados de pesquisa ja produzidos."""

    def simulate(
        self,
        weights: AllocationWeightResult,
        results: tuple[ResearchExecutionResult, ...],
    ) -> AllocationSimulationResult:
        """Combina curvas existentes sem executar novas estrategias."""
        weighted_curves = self._weighted_curves(weights, results)
        portfolio_curve = self._portfolio_curve(weighted_curves)
        portfolio_return = self._portfolio_return(portfolio_curve)
        portfolio_drawdown = self._portfolio_drawdown(portfolio_curve)
        portfolio_volatility = self._portfolio_volatility(portfolio_curve)

        return AllocationSimulationResult(
            portfolio_equity_curve=portfolio_curve,
            portfolio_return=portfolio_return,
            portfolio_drawdown=portfolio_drawdown,
            portfolio_volatility=portfolio_volatility,
        )

    def _weighted_curves(
        self,
        weights: AllocationWeightResult,
        results: tuple[ResearchExecutionResult, ...],
    ) -> tuple[tuple[float, ...], ...]:
        allocation = dict(weights.risk_adjusted_weight)
        alpha_ids = tuple(allocation.keys())
        curves: list[tuple[float, ...]] = []
        for index, result in enumerate(results):
            alpha_id = str(getattr(result, "alpha_id", alpha_ids[index] if index < len(alpha_ids) else ""))
            weight = allocation.get(alpha_id, 0.0)
            curve = tuple(point * weight for point in result.drawdown.equity_curve)
            if curve:
                curves.append(curve)
        return tuple(curves)

    def _portfolio_curve(
        self,
        curves: tuple[tuple[float, ...], ...],
    ) -> tuple[float, ...]:
        if not curves:
            return ()
        size = max(len(curve) for curve in curves)
        portfolio: list[float] = []
        for index in range(size):
            value = sum(
                curve[index] if index < len(curve) else curve[-1]
                for curve in curves
            )
            portfolio.append(value)
        return tuple(portfolio)

    def _portfolio_return(self, curve: tuple[float, ...]) -> float:
        if len(curve) < 2:
            return 0.0
        return curve[-1] - curve[0]

    def _portfolio_drawdown(self, curve: tuple[float, ...]) -> float:
        peak = None
        drawdown = 0.0
        for value in curve:
            peak = value if peak is None else max(peak, value)
            drawdown = max(drawdown, peak - value)
        return drawdown

    def _portfolio_volatility(self, curve: tuple[float, ...]) -> float:
        if len(curve) < 2:
            return 0.0
        returns = tuple(
            curve[index] - curve[index - 1]
            for index in range(1, len(curve))
        )
        average = sum(returns) / len(returns)
        variance = sum(
            (value - average) ** 2
            for value in returns
        ) / len(returns)
        return math.sqrt(variance)
