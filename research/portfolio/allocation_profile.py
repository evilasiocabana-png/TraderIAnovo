"""Contrato oficial de perfil de alocacao."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AllocationProfile:
    """Representa um perfil de alocacao do TraderIA_WDO."""

    profile_id: str
    name: str
    description: str
    capital: float
    allocation_method: str
    alpha_ids: tuple[str, ...]
    max_allocation_per_alpha: float
    max_total_exposure: float
    created_at: str
    metadata: Mapping[str, object]
