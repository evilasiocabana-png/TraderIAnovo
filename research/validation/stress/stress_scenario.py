"""Contrato oficial dos cenarios de estresse."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class StressScenarioType(Enum):
    """Tipos oficiais de cenarios de estresse."""

    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    GAP_UP = "GAP_UP"
    GAP_DOWN = "GAP_DOWN"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    TRENDING_MARKET = "TRENDING_MARKET"
    RANGING_MARKET = "RANGING_MARKET"
    BLACK_SWAN = "BLACK_SWAN"


@dataclass(frozen=True)
class StressScenario:
    """Representa um cenario declarativo de estresse."""

    scenario_id: str
    scenario_type: StressScenarioType
    description: str
    severity: float
    enabled: bool
    metadata: Mapping[str, object]
