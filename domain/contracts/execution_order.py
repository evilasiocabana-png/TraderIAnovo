"""Contrato de ordem operacional normalizada."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionOrder:
    """DTO padrao para ordens de execucao."""

    side: str
    quantity: float
    entry_price: float
    stop: float
    target: float
    symbol: str = "UNKNOWN"
