"""Perfil oficial de uma estrategia do TraderIA_WDO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class StrategyProfile:
    """Representa o perfil completo de uma estrategia."""

    strategy_id: str
    name: str
    family: str
    asset_class: str
    supported_markets: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    holding_period: str
    research_status: str
    version: str
    metadata: Mapping[str, object]
