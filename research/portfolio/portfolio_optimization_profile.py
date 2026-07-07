"""Contrato oficial de perfil de otimizacao de portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from research.portfolio.allocation_profile import AllocationProfile


OptimizationGoal = Literal["MAX_RETURN", "MIN_RISK", "BALANCED"]


@dataclass(frozen=True)
class PortfolioOptimizationProfile:
    """Representa um perfil declarativo de otimizacao de portfolio."""

    profile_id: str
    capital: float
    allocation_method: str
    optimization_goal: OptimizationGoal
    alpha_ids: tuple[str, ...]
    constraints: Mapping[str, object]
    created_at: str
    metadata: Mapping[str, object]

    @classmethod
    def from_allocation_profile(
        cls,
        allocation_profile: AllocationProfile,
        optimization_goal: OptimizationGoal,
        constraints: Mapping[str, object],
    ) -> "PortfolioOptimizationProfile":
        """Cria perfil de otimizacao a partir do AllocationProfile existente."""
        return cls(
            profile_id=allocation_profile.profile_id,
            capital=allocation_profile.capital,
            allocation_method=allocation_profile.allocation_method,
            optimization_goal=optimization_goal,
            alpha_ids=allocation_profile.alpha_ids,
            constraints=constraints,
            created_at=allocation_profile.created_at,
            metadata=allocation_profile.metadata,
        )
