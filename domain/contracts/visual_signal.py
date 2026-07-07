from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualSignal:
    symbol: str
    timeframe: str
    decision: str
    entry: float | None
    stop: float | None
    target: float | None
    setup: str
    reason: str
    stop_management: str
    is_positioned: bool = False
    position_open_time: str | None = None
