"""Perfil oficial de validacao Walk-Forward."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class WalkForwardProfile:
    """Representa um perfil declarativo de validacao Walk-Forward."""

    profile_id: str
    training_window: int
    validation_window: int
    testing_window: int
    rolling_window: int
    minimum_samples: int
    metadata: Mapping[str, object]
