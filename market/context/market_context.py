"""Contrato oficial de contexto de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class MarketContext:
    """Representa o contexto consolidado do mercado."""

    timestamp: str
    regime: str
    volatility: float
    liquidity: float
    momentum: float
    session: str
    market_dna: Mapping[str, object]
    confidence: float
    metadata: Mapping[str, object]
