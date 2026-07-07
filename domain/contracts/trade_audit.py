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
    dynamic_exit_policy: str = "N/D"
    dynamic_exit_action: str = "N/D"
    dynamic_exit_reason: str = "N/D"
    dynamic_exit_confidence: float = 0.0
    dynamic_exit_market_state: str = "NO_POSITION"
    dynamic_exit_r_multiple: float = 0.0
    dynamic_exit_candidate_stop: float | None = None
    dynamic_exit_allowed_to_execute_demo: bool = False
    dynamic_exit_executed_action: str = "NONE"
    dynamic_exit_final_result: str = "N/D"


@dataclass(frozen=True)
class TradeAuditReport:
    status: str
    source: str
    total_rows: int
    rows: list[TradeAuditRow]
    message: str
    total_open_positions: int = 0
    open_profit: float = 0.0
