"""Status read-only do MT5."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MT5Status:
    status: str
    server: str
    account: str
    timeframe: str
    connected: bool = False
    message: str = "MT5 nao conectado."
