"""Contrato oficial de definicao de feature."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDefinition:
    """Representa a definicao declarativa de uma feature."""

    feature_id: str
    name: str
    description: str
    category: str
    timeframe: str
    data_type: str
    source: str
    version: int
    author: str
    created_at: str
    enabled: bool
