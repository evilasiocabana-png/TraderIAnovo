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
    dynamic_exit_policy: str = "FIXED_STOP"
    dynamic_exit_action: str = "KEEP_ORIGINAL_PLAN"
    dynamic_exit_reason: str = "Saida dinamica read-only ainda sem ajuste operacional."
    dynamic_exit_confidence: float = 0.0
    dynamic_exit_market_state: str = "NO_POSITION"
    dynamic_exit_r_multiple: float = 0.0
    dynamic_exit_candidate_stop: float | None = None
    dynamic_exit_allowed_to_execute_demo: bool = False
    dynamic_exit_source: str = "DYNAMIC_EXIT_READ_ONLY"
    is_positioned: bool = False
    position_side: str = "N/D"
    position_volume: float = 0.0
    position_price: float | None = None
    position_profit: float = 0.0
