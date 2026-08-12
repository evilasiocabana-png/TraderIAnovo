"""Politica unica de ativacao dos modelos operacionais TraderIA."""

from __future__ import annotations

import re


ACTIVE_OPERATIONAL_MODEL_NUMBERS = frozenset(range(1, 8))
RETIRED_OPERATIONAL_MODEL_NUMBERS = frozenset(range(8, 23))
ACTIVE_SCOPED_MODEL_IDS = frozenset(
    {
        "MODELO_3_XAU_M5_RSI50_FLIP",
        "MODELO_6_LAB_FOREX_EXPANSION",
        "MODELO_7_LAB_XAU_BTC",
        "MODELO_8_XAU_M5_SMA_RSI_REENTRY",
        "MODELO_9_XAU_M5_SMA_RSI_ADX",
        "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
        "MODELO_11_XAU_M5_SMA_RSI_SMA50_SLOPE",
        "MODELO_12_XAU_M5_SMA_RSI_TREND_FILTERS",
        "MODELO_13_FOREX_M5_SMA_RSI_REENTRY",
        "MODELO_14_FOREX_M5_SMA_RSI_ADX",
        "MODELO_15_FOREX_M5_SMA_RSI_MA_DISTANCE_ATR",
        "MODELO_16_FOREX_M5_SMA_RSI_SMA50_SLOPE",
        "MODELO_17_FOREX_M5_SMA_RSI_TREND_FILTERS",
    }
)
RETIRED_LEGACY_MODEL_IDS = frozenset(
    {
        "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS",
        "MODELO_3_RR3",
        "MODELO_3_LAB_ALL_FOREX_WINNERS",
        "MODELO_6_TREND_MOMENTUM_ORIGINAL",
        "MODELO_6_ESPELHO_M5",
        "MODELO_7_TREND_MOMENTUM_DYNAMIC",
    }
)


def operational_model_number(value: object) -> int | None:
    """Extrai M1..M22 de IDs canonicos, aliases e comentarios de auditoria."""
    normalized = str(value or "").strip().upper()
    match = re.search(r"(?:MODELO[_ ]?|(?:^|[\s|])M)(\d{1,2})(?:_|\b|$)", normalized)
    if match is None:
        return None
    number = int(match.group(1))
    return number if 1 <= number <= 22 else None


def is_active_operational_model(value: object) -> bool:
    """Retorna True somente para os modelos autorizados a abrir novas ordens."""
    normalized = str(value or "").strip().upper()
    if normalized in RETIRED_LEGACY_MODEL_IDS:
        return False
    number = operational_model_number(normalized)
    return number in range(1, 6) or normalized in ACTIVE_SCOPED_MODEL_IDS


def is_retired_operational_model(value: object) -> bool:
    """Retorna True para legados e M8..M22, exceto IDs novos explicitamente ativos."""
    normalized = str(value or "").strip().upper()
    if normalized in ACTIVE_SCOPED_MODEL_IDS:
        return False
    return (
        normalized in RETIRED_LEGACY_MODEL_IDS
        or operational_model_number(normalized) in RETIRED_OPERATIONAL_MODEL_NUMBERS
    )


def is_dynamic_exit_operational_model(value: object) -> bool:
    """M8-M14 are preserved only for historical compatibility."""
    normalized = str(value or "").strip().upper()
    return normalized in ACTIVE_SCOPED_MODEL_IDS and any(
        normalized.startswith(f"MODELO_{number}_DYNAMIC_EXIT_FROM_M")
        for number in range(8, 15)
    )
