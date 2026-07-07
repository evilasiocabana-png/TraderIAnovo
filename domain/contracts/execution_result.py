"""Contrato de resultado de execucao normalizada."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    """DTO padrao para retorno de um adaptador de execucao."""

    accepted: bool
    status: str
    message: str
    ticket: int | None = None
    executed_price: float | None = None
    error_code: int | None = None
