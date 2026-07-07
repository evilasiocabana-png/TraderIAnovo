"""Relatorio oficial da pesquisa de alocacao."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.portfolio.allocation_profile import AllocationProfile
from research.portfolio.allocation_risk_engine import AllocationRiskResult
from research.portfolio.allocation_simulation import AllocationSimulationResult
from research.portfolio.allocation_weight_engine import AllocationWeightResult


@dataclass(frozen=True)
class AllocationReport:
    """Consolida os resultados produzidos pela pesquisa de alocacao."""

    profile: AllocationProfile
    weights: AllocationWeightResult
    risk: AllocationRiskResult
    simulation: AllocationSimulationResult
    allocation_method: str
    alpha_weights: Mapping[str, float]
    portfolio_return: float
    aggregate_drawdown: float
    aggregate_risk_score: float
    portfolio_equity_curve: tuple[float, ...]
    execution_time: float
    metadata: Mapping[str, object]
