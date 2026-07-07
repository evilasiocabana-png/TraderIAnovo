"""Contrato de resultado teorico do Lab."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LabResult:
    setup: str
    timeframe: str
    theoretical_entry: str
    interest_zone: str
    stop_management: str
    parameters: dict[str, str] = field(default_factory=dict)
