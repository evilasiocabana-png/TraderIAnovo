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
