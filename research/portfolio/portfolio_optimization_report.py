"""Relatorio oficial da otimizacao de portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.portfolio.allocation_simulation import (
    AllocationSimulationResult as PortfolioSimulationResult,
)
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.portfolio.portfolio_risk_engine import PortfolioRiskResult


@dataclass(frozen=True)
class PortfolioOptimizationReport:
    """Consolida resultados da otimizacao de portfolio sem calcular."""

    optimization: PortfolioOptimizationResult
    risk: PortfolioRiskResult
    simulation: PortfolioSimulationResult
    optimization_goal: str
    allocation_method: str
    alpha_weights: Mapping[str, float]
    expected_return: float
    aggregate_drawdown: float
    diversification_score: float
    aggregate_risk: float
    execution_time: float
    metadata: Mapping[str, object]
