"""Contrato canonico da janela deslizante usada pelos indicadores operacionais."""

from __future__ import annotations

from typing import Iterable, TypeVar


T = TypeVar("T")

OPERATIONAL_INDICATOR_CLOSED_CANDLES = 200
OPERATIONAL_INDICATOR_RAW_CANDLES = OPERATIONAL_INDICATOR_CLOSED_CANDLES + 1
OPERATIONAL_INDICATOR_SOURCE = "LOCAL_MT5_CLOSED_CANDLES_200"
LEGACY_OPERATIONAL_INDICATOR_SOURCES = frozenset({"LOCAL_MT5_CANDLES_52"})


def operational_raw_window(rows: Iterable[T]) -> list[T]:
    """Mantem 200 velas fechadas mais a vela atual ainda em formacao."""
    return list(rows or ())[-OPERATIONAL_INDICATOR_RAW_CANDLES:]


def operational_closed_window(rows: Iterable[T]) -> list[T]:
    """Retorna exclusivamente as 200 velas fechadas da janela operacional."""
    raw = operational_raw_window(rows)
    if len(raw) < OPERATIONAL_INDICATOR_RAW_CANDLES:
        return []
    return raw[:-1]
