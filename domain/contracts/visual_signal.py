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
    alpha_id: str = "ALPHA001"
    beta_id: str = "LEGACY_CURRENT_EXIT"
    beta_version: str = "BETA v1"
    beta_mode: str = "PROTECT_ONLY"
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
    position_open_time: str | None = None
