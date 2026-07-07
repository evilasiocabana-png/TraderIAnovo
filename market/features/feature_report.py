"""Relatorio oficial de features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from market.features.feature_definition import FeatureDefinition
from market.features.feature_validator import FeatureValidationResult


@dataclass(frozen=True)
class FeatureReport:
    """Consolida resultados produzidos por componentes de features."""

    feature_definitions: tuple[FeatureDefinition, ...]
    validation_results: tuple[FeatureValidationResult, ...]
    calculated_values: Mapping[str, object]
    execution_time_ms: float
