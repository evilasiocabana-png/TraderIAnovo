"""Perfil oficial de configuracao das pesquisas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.research_timeframe_profile import ResearchTimeframeProfile


@dataclass(frozen=True)
class ResearchConfigurationProfile:
    """Representa uma configuracao declarativa de pesquisa."""

    strategy_family: str
    timeframe_profile: ResearchTimeframeProfile
    minimum_sample_size: int
    required_metrics: tuple[str, ...]
    validation_rules: tuple[str, ...]
    campaign_profile: Mapping[str, object]
