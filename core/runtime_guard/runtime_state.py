"""Classificacao de estado do Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RuntimeStateCategory(StrEnum):
    """Categorias canonicas de estado runtime."""

    OPERACIONAL_PROTEGIDO = "OPERACIONAL_PROTEGIDO"
    VISUAL_PRESERVAVEL = "VISUAL_PRESERVAVEL"
    TEMPORARIO_LIMPAVEL = "TEMPORARIO_LIMPAVEL"
    DIAGNOSTICO = "DIAGNOSTICO"
    PERSISTENTE = "PERSISTENTE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuntimeStateEntry:
    """Item classificado de estado de runtime."""

    key: str
    value: Any
    category: RuntimeStateCategory = RuntimeStateCategory.UNKNOWN
    updated_at: float = 0.0


PROTECTED_STATE_KEYS = frozenset(
    {
        "dashboard_service",
        "mt5_demo_robot_online_enabled",
        "mt5_demo_robot_last_visible_snapshot",
        "mt5_forex_last_valid_snapshot",
        "mt5_lab_last_valid_suggestions",
        "mt5_trade_audit_report_cache",
    }
)

TEMPORARY_STATE_KEYS = frozenset(
    {
        "mt5_forex_manual_diagnostic",
        "mt5_forex_manual_diagnostic_message",
        "mt5_forex_initial_load_error",
        "mt5_forex_last_auto_load_at",
        "mt5_report_last_auto_load_at",
        "mt5_demo_robot_last_cycle_monotonic",
        "mt5_demo_robot_message",
        "ui_last_critical_interaction_at",
        "runtime_cleanup_message",
        "runtime_event_log",
    }
)

VISUAL_STATE_PREFIXES = (
    "mt5_trade_audit_report_",
    "runtime_render_",
)

TEMPORARY_STATE_PREFIXES = (
    "runtime_temp_",
    "replay_pending_",
)

DIAGNOSTIC_STATE_PREFIXES = (
    "runtime_diag_",
    "runtime_health_",
)


def classify_runtime_state_key(key: str) -> RuntimeStateCategory:
    """Classifica chaves conhecidas sem inferir permissao destrutiva."""
    if key in PROTECTED_STATE_KEYS:
        return RuntimeStateCategory.OPERACIONAL_PROTEGIDO
    if key in TEMPORARY_STATE_KEYS:
        return RuntimeStateCategory.TEMPORARIO_LIMPAVEL
    if key.startswith(VISUAL_STATE_PREFIXES):
        return RuntimeStateCategory.VISUAL_PRESERVAVEL
    if key.startswith(TEMPORARY_STATE_PREFIXES):
        return RuntimeStateCategory.TEMPORARIO_LIMPAVEL
    if key.startswith(DIAGNOSTIC_STATE_PREFIXES):
        return RuntimeStateCategory.DIAGNOSTICO
    return RuntimeStateCategory.UNKNOWN
