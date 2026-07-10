"""Linha de relatorio consolidado."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    section: str
    status: str
    detail: str
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
    final_exit_reason: str = "N/D"
