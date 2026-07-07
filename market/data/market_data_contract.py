"""Contrato normalizado para dados de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class MarketDataContract:
    """Representa um candle normalizado consumido pela plataforma."""

    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_valid: bool
    metadata: Mapping[str, object]
