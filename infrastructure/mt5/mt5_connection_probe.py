"""Sonda futura de conexao MT5 read-only."""

from __future__ import annotations


def probe_connection() -> dict[str, object]:
    return {
        "ok": False,
        "mode": "read-only",
        "message": "Sonda placeholder sem conexao operacional.",
    }
