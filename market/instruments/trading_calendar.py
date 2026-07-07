"""Contrato oficial de calendario de negociacao."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TradingCalendar:
    """Representa a estrutura declarativa de um calendario de negociacao."""

    calendar_id: str
    business_days: tuple[str, ...]
    holidays: tuple[str, ...]
    sessions: tuple[str, ...]
    market_open: str
    market_close: str
    special_hours: Mapping[str, str]
    metadata: Mapping[str, object]
