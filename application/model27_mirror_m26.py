"""Contrato operacional do Modelo 27, espelho independente do Modelo 26."""

from __future__ import annotations

from dataclasses import dataclass

from application.model26_xau_m5_smart_money import (
    MODEL_26_ID,
    MODEL_26_SYMBOL,
    MODEL_26_TIMEFRAME,
)


MODEL_27_ID = "MODELO_27_ESPELHO_M26"
MODEL_27_ALPHA_ID = "ALPHA027_M26_MIRROR"
MODEL_27_ALPHA_VERSION = "M27_ENTRY_V1"
MODEL_27_BETA_ID = "BETA027_FIXED_RR1"
MODEL_27_BETA_VERSION = "M27_EXIT_V1"
MODEL_27_SOURCE = "MODEL_27_MIRROR_M26"
MODEL_27_STOP_MANAGEMENT = "M27_FIXED_SL_TP_RR1"
MODEL_27_SYMBOL = MODEL_26_SYMBOL
MODEL_27_TIMEFRAME = MODEL_26_TIMEFRAME
MODEL_27_VOLUME = 0.03
MODEL_27_CONTRACT_VERSION = "M27_MIRROR_M26_V1"

_ORDER_TYPE_MIRROR = {
    "MARKET": "MARKET",
    "BUY_STOP": "SELL_LIMIT",
    "SELL_STOP": "BUY_LIMIT",
    "BUY_LIMIT": "SELL_STOP",
    "SELL_LIMIT": "BUY_STOP",
}


@dataclass(frozen=True)
class Model27MirrorGeometry:
    direction: str
    entry_price: float
    stop: float
    target: float
    risk_reward: float = 1.0


def is_model27(model: object) -> bool:
    return str(model or "").strip().upper() == MODEL_27_ID


def mirror_model26_order_type(order_type: object) -> str:
    normalized = str(order_type or "MARKET").strip().upper()
    try:
        return _ORDER_TYPE_MIRROR[normalized]
    except KeyError as exc:
        raise ValueError(f"Tipo de ordem M26 sem espelho M27: {normalized}") from exc


def mirror_model26_geometry(
    direction: object,
    entry_price: object,
    source_stop: object,
) -> Model27MirrorGeometry:
    source_direction = str(direction or "").strip().upper()
    if source_direction not in {"BUY", "SELL"}:
        raise ValueError("Direcao M26 deve ser BUY ou SELL para gerar o M27.")
    entry = float(entry_price)
    target = float(source_stop)
    distance = abs(entry - target)
    if entry <= 0.0 or target <= 0.0 or distance <= 0.0:
        raise ValueError("Entrada e SL do M26 devem formar distancia positiva.")
    mirrored_direction = "SELL" if source_direction == "BUY" else "BUY"
    mirrored_stop = entry + distance if mirrored_direction == "SELL" else entry - distance
    return Model27MirrorGeometry(
        direction=mirrored_direction,
        entry_price=entry,
        stop=mirrored_stop,
        target=target,
    )


def model27_parameters() -> dict[str, object]:
    return {
        "source_operational_model": MODEL_26_ID,
        "mirror_contract": MODEL_27_CONTRACT_VERSION,
        "mirror_direction": True,
        "target_from_source_stop": True,
        "risk_reward": 1.0,
        "execution_volume": MODEL_27_VOLUME,
        "demo_only": True,
    }
