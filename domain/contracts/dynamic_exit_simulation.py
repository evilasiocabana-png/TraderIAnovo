"""Contrato de decisao simulada/paper para saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicExitSimulationDecision:
    """Decisao paper de stop dinamico, sem execucao operacional."""

    symbol: str
    ticket: int | None = None
    side: str = "N/D"
    policy: str = "FIXED_STOP"
    action: str = "KEEP_ORIGINAL_PLAN"
    current_stop: float | None = None
    candidate_stop: float | None = None
    approved_stop: float | None = None
    allowed_to_simulate: bool = False
    rejection_reasons: tuple[str, ...] = ()
    market_state: str = "NO_POSITION"
    r_multiple: float = 0.0
    source: str = "DYNAMIC_EXIT_SIMULATION"
    created_at: str = "N/D"
    candle_key: str = "N/D"
