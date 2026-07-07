"""Contrato oficial das bolsas suportadas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Exchange:
    """Representa uma bolsa de negociacao suportada."""

    exchange_id: str
    name: str
    timezone: str
    country: str
    currency: str
    calendar_id: str
    metadata: Mapping[str, object]


B3_EXCHANGE = Exchange(
    exchange_id="B3",
    name="Brasil, Bolsa, Balcao",
    timezone="America/Sao_Paulo",
    country="BR",
    currency="BRL",
    calendar_id="B3",
    metadata={"status": "supported"},
)

SUPPORTED_EXCHANGES: tuple[Exchange, ...] = (B3_EXCHANGE,)

FUTURE_EXCHANGE_IDS: tuple[str, ...] = (
    "CME",
    "NYSE",
    "NASDAQ",
    "ICE",
)
