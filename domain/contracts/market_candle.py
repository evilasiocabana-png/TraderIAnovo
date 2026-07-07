"""Contrato de candle de mercado."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketCandle:
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    timestamp: str
