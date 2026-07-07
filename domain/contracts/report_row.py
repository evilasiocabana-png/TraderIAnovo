"""Linha de relatorio consolidado."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    section: str
    status: str
    detail: str
