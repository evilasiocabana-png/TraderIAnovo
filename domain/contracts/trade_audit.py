from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeAuditRow:
    symbol: str
    status: str
    source: str
    lab_decision: str
    mt5_position_status: str
    message: str
    side: str = "N/D"
    volume: float = 0.0
    entry_price: float | None = None
    current_price: float | None = None
    profit: float = 0.0


@dataclass(frozen=True)
class TradeAuditReport:
    status: str
    source: str
    total_rows: int
    rows: list[TradeAuditRow]
    message: str
    total_open_positions: int = 0
    open_profit: float = 0.0
