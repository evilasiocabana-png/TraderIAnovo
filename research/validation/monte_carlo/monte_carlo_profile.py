"""Perfil oficial de validacao Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class MonteCarloProfile:
    """Representa um perfil declarativo de validacao Monte Carlo."""

    profile_id: str
    simulations: int
    random_seed: int
    confidence_level: float
    resampling_method: str
    metadata: Mapping[str, object]
