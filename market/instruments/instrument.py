"""Contrato oficial de instrumento financeiro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Instrument:
    """Representa um instrumento financeiro negociavel."""

    instrument_id: str
    symbol: str
    asset_class: str
    exchange: str
    currency: str
    tick_size: float
    point_value: float
    contract_size: float
    enabled: bool
    metadata: Mapping[str, object]
