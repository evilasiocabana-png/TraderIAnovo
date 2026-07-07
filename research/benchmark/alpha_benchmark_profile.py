"""Contrato oficial de benchmark entre Alphas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AlphaBenchmarkProfile:
    """Representa um benchmark declarativo entre duas Alphas."""

    benchmark_id: str
    alpha_a: str
    alpha_b: str
    experiment_ids: tuple[str, ...]
    campaign_ids: tuple[str, ...]
    comparison_period: str
    metrics: tuple[str, ...]
    created_at: str
    metadata: Mapping[str, object]
