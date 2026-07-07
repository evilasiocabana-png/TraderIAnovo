"""Contrato oficial de definicao de experimento."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ExperimentDefinition:
    """Representa um experimento de pesquisa do TraderIA_WDO."""

    experiment_id: str
    alpha_id: str
    alpha_version: str
    configuration_version: str
    replay_period: str
    dataset: str
    status: str
    priority: int
    created_at: str
    metadata: Mapping[str, object]
