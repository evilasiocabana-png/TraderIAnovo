"""Contrato de execucao assistida de SL demo para saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicExitDemoSLExecutionResult:
    """Resultado auditavel da tentativa assistida de modificar somente SL."""

    symbol: str
    ticket: int | None
    side: str
    requested_stop: float | None
    previous_stop: float | None = None
    new_stop: float | None = None
    allowed: bool = False
    submitted: bool = False
    success: bool = False
    retcode: str = "N/D"
    message: str = "Execucao assistida nao solicitada."
    rejection_reasons: tuple[str, ...] = ()
    source: str = "DYNAMIC_EXIT_DEMO_SL_ASSISTED"
    created_at: str = "N/D"
