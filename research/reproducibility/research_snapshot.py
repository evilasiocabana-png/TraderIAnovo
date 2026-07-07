"""Snapshot oficial de uma execucao de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResearchSnapshot:
    """Representa o estado completo usado em uma execucao de pesquisa."""

    snapshot_id: str
    experiment_id: str
    alpha_id: str
    alpha_version: str
    configuration_version: str
    feature_version: str
    context_version: str
    risk_version: str
    research_pipeline_version: str
    replay_period: str
    dataset: str
    random_seed: int
    created_at: str
    metadata: Mapping[str, object]
