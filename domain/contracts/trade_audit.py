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


@dataclass(frozen=True)
class TradeAuditReport:
    status: str
    source: str
    total_rows: int
    rows: list[TradeAuditRow]
    message: str
