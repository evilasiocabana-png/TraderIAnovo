"""Contrato de pre-autorizacao demo da saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicExitDemoAuthorization:
    """Resultado auditavel antes de qualquer permissao operacional de demo."""

    policy: str = "N/D"
    action: str = "N/D"
    status: str = "REJECTED"
    reason: str = "Pre-autorizacao demo nao avaliada."
    eligible_to_authorize: bool = False
    allowed_to_execute_demo: bool = False
    candidate_stop: float | None = None
    market_state: str = "NO_POSITION"
    execution_mode: str = "READ_ONLY_PRE_AUTHORIZATION"
    source: str = "DYNAMIC_EXIT_BREAK_EVEN_DEMO_AUTHORIZER"
