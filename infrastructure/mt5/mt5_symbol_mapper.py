"""Mapeamento simples de simbolos Forex."""

from __future__ import annotations


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "")
