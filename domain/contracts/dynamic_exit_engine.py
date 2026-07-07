"""Contrato do motor unificado read-only de saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


@dataclass(frozen=True)
class DynamicExitEngineInput:
    """Entrada unica para o motor unificado de saida dinamica."""

    reading: DynamicExitMarketReading
    policy: str = "FIXED_STOP"
    plan_status: str = "PLANO_VALIDO"
    recommendation: DynamicExitRecommendation | None = None


@dataclass(frozen=True)
class DynamicExitEngineResult:
    """Resultado auditavel do motor unificado, sem permissao operacional."""

    policy: str
    market_reading: DynamicExitMarketReading
    recommendation: DynamicExitRecommendation
    authorization: DynamicExitDemoAuthorization
    allowed_to_execute_demo: bool = False
    execution_mode: str = "READ_ONLY_UNIFIED_ENGINE"
    source: str = "DYNAMIC_EXIT_UNIFIED_ENGINE_READ_ONLY"
