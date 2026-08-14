"""Regressoes da fronteira entre IDs canonicos ativos e IDs historicos."""

from __future__ import annotations

from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)


ACTIVE_SCOPED_IDS = (
    "MODELO_8_XAU_M5_SMA_RSI_REENTRY",
    "MODELO_21_XAU_M5_SMA_RSI_SMA50_SLOPE_REENTRY_TP75",
    "MODELO_22_XAU_M5_SMA_RSI_TREND_FILTERS_REENTRY_TP75",
)

RETIRED_LEGACY_IDS = (
    "MODELO_8_DYNAMIC_EXIT_FROM_M1",
    "MODELO_9_DYNAMIC_EXIT_FROM_M2",
    "MODELO_10_DYNAMIC_EXIT_FROM_M3",
    "MODELO_11_DYNAMIC_EXIT_FROM_M4",
    "MODELO_12_DYNAMIC_EXIT_FROM_M5",
    "MODELO_13_DYNAMIC_EXIT_FROM_M6",
    "MODELO_14_DYNAMIC_EXIT_FROM_M7",
    "MODELO_8_TREND_PULLBACK_H1_M5",
    "MODELO_21_ESPELHO_M19",
    "MODELO_22_ESPELHO_M9",
)


def test_ids_canonicos_atuais_permanecem_ativos() -> None:
    for model_id in ACTIVE_SCOPED_IDS:
        assert is_active_operational_model(model_id), model_id
        assert not is_retired_operational_model(model_id), model_id


def test_ids_historicos_nao_escapam_pelo_numero_ativo() -> None:
    for model_id in RETIRED_LEGACY_IDS:
        assert not is_active_operational_model(model_id), model_id
        assert is_retired_operational_model(model_id), model_id
