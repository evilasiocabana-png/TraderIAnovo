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
    dynamic_exit_allowed_to_execute_demo: bool = False
