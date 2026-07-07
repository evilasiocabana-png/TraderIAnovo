"""Contrato de sinal Forex read-only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForexSignal:
    pair: str
    timeframe: str
    decision: str
    price: float
    reason: str
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    last_update: str = "N/D"
    lab_setup: str = "N/D"
    stop_management: str = "N/D"
    is_positioned: bool = False
    position_side: str = "N/D"
    position_volume: float = 0.0
    position_price: float | None = None
    position_profit: float = 0.0
