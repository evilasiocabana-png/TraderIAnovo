"""Modelo 24: cesta XAU/M5 com entradas RSI50 e alvo financeiro global."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterable, Protocol
from uuid import uuid4

from application.model24_setup_contract import (
    MODEL_24_SETUP,
    MODEL_24_SETUP_CONTRACT_FINGERPRINT,
    MODEL_24_SETUP_CONTRACT_VERSION,
)

MODEL_24_ID = MODEL_24_SETUP.model_id
MODEL_24_ALPHA_ID = "ALPHA024_XAU_RSI50_MULTI_SOURCE"
MODEL_24_ALPHA_VERSION = "M24_ENTRY_V1"
MODEL_24_BETA_ID = "BETA024_BASKET_FULL_EXIT_1000"
MODEL_24_BETA_VERSION = "M24_EXIT_V1"
MODEL_24_ENTRY_SOURCE = "MODEL_24_XAU_SOURCE_SIGNAL"
MODEL_24_EXIT_POLICY = "M24_SOURCE_EXIT_PLUS_BASKET_1000"
MODEL_24_FULL_EXIT_USD = MODEL_24_SETUP.basket_full_exit_usd
MODEL_24_INITIAL_VOLUME = MODEL_24_SETUP.initial_volume
MODEL_24_REENTRY_VOLUME = MODEL_24_SETUP.reentry_volume
MODEL_24_CONTINUATION_VOLUME = MODEL_24_SETUP.continuation_volume
MODEL_24_LATERALIZATION_VOLUME = MODEL_24_SETUP.lateralization_volume
MODEL_24_INITIAL_TARGET_DISTANCE = MODEL_24_SETUP.initial_target_distance
MODEL_24_CONTINUATION_TARGET_DISTANCE = (
    MODEL_24_SETUP.continuation_target_distance
)
MODEL_24_PIP_SIZE = MODEL_24_SETUP.pip_size
MODEL_24_ATR_PERIOD = MODEL_24_SETUP.atr_period
MODEL_24_DISTANCE_ATR_MIN = MODEL_24_SETUP.distance_atr_min
MODEL_24_TIMEFRAME = MODEL_24_SETUP.timeframe
MODEL_24_SYMBOL = MODEL_24_SETUP.symbol
MODEL_24_RUNTIME_SOURCE = MODEL_24_SETUP.runtime_source
MODEL_24_STATE_PATH = Path(".traderia") / "model24_basket_state.json"
MODEL_24_RUNTIME_STATE_PATH = Path(".traderia") / "model24_runtime_state.json"
MODEL_24_AUDIT_PATH = Path(".traderia") / "model24_basket_audit.jsonl"
MODEL_24_LEGACY_SOURCE_MODEL_NUMBERS = (8, 10, 18, 19, 20, 21, 22)
MODEL_24_LEGACY_SOURCE_MODEL_IDS = (
    "MODELO_8_XAU_M5_SMA_RSI_REENTRY",
    "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
    "MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75",
    "MODELO_19_XAU_M5_SMA_RSI_ADX_REENTRY_TP75",
    "MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75",
    "MODELO_21_XAU_M5_SMA_RSI_SMA50_SLOPE_REENTRY_TP75",
    "MODELO_22_XAU_M5_SMA_RSI_TREND_FILTERS_REENTRY_TP75",
)
# O runtime atual calcula um unico M24 autonomo. A lista legada acima existe
# apenas para reconhecer snapshots, comentarios e historicos anteriores.
MODEL_24_SOURCE_MODEL_NUMBERS = MODEL_24_LEGACY_SOURCE_MODEL_NUMBERS
MODEL_24_SOURCE_MODEL_IDS = (MODEL_24_ID,)

_LOCK = threading.RLock()


class Model24ExecutionPort(Protocol):
    def list_open_positions(self) -> list[object]: ...

    def close_position(
        self, *, symbol: str, ticket: int, side: str, volume: float, reason: str
    ) -> object: ...


def operational_model_number(value: object) -> int | None:
    match = re.search(
        r"(?:MODELO[_ ]?|(?:^|[\s|])M)(\d{1,2})(?:_|\b|$)",
        str(value or "").upper(),
    )
    return int(match.group(1)) if match is not None else None


def is_model24(value: object) -> bool:
    return str(value or "").upper().startswith(MODEL_24_ID)


def model24_variant_id(source_operational_model: object) -> str:
    """Retorna a identidade unica usada por novas ordens M24.

    O argumento permanece por compatibilidade com chamadas antigas. Variantes
    ``SOURCE_M<n>`` continuam reconhecidas em historicos, mas nao sao mais
    produzidas pelo runtime.
    """
    del source_operational_model
    return MODEL_24_ID


def model24_source_model_id(value: object) -> str:
    normalized = str(value or "").upper()
    if normalized == MODEL_24_ID:
        return MODEL_24_RUNTIME_SOURCE
    match = re.search(r"_SOURCE_M(\d{1,2})(?:_|\b|$)", normalized)
    return f"M{int(match.group(1))}" if match is not None else "N/D"


def model24_order_comment(value: object) -> str:
    source = model24_source_model_id(value)
    return (
        "TraderIA M24"
        if source in {"N/D", MODEL_24_RUNTIME_SOURCE}
        else f"TraderIA M24 S{source[1:]}"
    )


def model24_position_matches(position: object) -> bool:
    return bool(re.search(r"\bM24\b", str(getattr(position, "comment", "") or "").upper()))


def model24_position_net(position: object) -> float:
    return sum(
        float(getattr(position, field, 0.0) or 0.0)
        for field in ("profit", "swap", "commission", "fee")
    )


def model24_market_entry_role(source_model: object, trend_side: object) -> str:
    """Alterna INITIAL globalmente; o mesmo lado produz apenas REENTRY."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        state = dict(dict(payload.get("sources") or {}).get(source) or {})
    last_initial_side = _model24_last_initial_side(payload)
    if not last_initial_side:
        # Compatibilidade com snapshots anteriores ao controle global.
        last_initial_side = str(state.get("trend_side") or "").upper()
    if last_initial_side != side:
        return "INITIAL"
    return "REENTRY"


def mark_model24_market_entry_accepted(
    source_model: object,
    trend_side: object,
    candle_time: object,
) -> None:
    """Confirma consumo somente depois de aceite do provider Demo."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        previous_side = str(state.get("trend_side") or "").upper()
        if previous_side and previous_side != side:
            for field_name in (
                "skip_first_reentry_after_extreme",
                "blocked_reentry_opportunity_key",
                "blocked_reentry_at",
                "released_reentry_opportunity_key",
                "continuation_status",
                "continuation_side",
                "continuation_target_price",
                "continuation_target_time",
                "continuation_armed_candle",
                "continuation_armed_at",
                "continuation_consumed_candle",
                "continuation_consumed_at",
                "continuation_target_exit_confirmed_at",
            ):
                state.pop(field_name, None)
        state.update({
            "trend_side": side,
            "initial_consumed": True,
            "last_entry_candle": str(candle_time or "N/D"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        sources[source] = state
        payload.update(
            {
                "sources": sources,
                "last_initial_side": side,
                "last_initial_source": source,
                "last_initial_candle": str(candle_time or "N/D"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_runtime_state(payload)


def mark_model24_reentry_target_armed(
    source_model: object,
    trend_side: object,
    target_price: object,
    target_time: object,
    candle_time: object,
) -> None:
    """Arma a CONTINUATION somente depois do aceite da REENTRY com TP."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    try:
        target = float(target_price)
    except (TypeError, ValueError):
        return
    if side not in {"BUY", "SELL"} or target <= 0.0:
        return
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        state.update(
            {
                "continuation_status": "WAITING_REENTRY_TARGET_EXIT",
                "continuation_side": side,
                "continuation_target_price": target,
                "continuation_target_time": str(target_time or "N/D"),
                "continuation_armed_candle": str(candle_time or "N/D"),
                "continuation_armed_at": datetime.now(timezone.utc).isoformat(),
                "continuation_target_exit_confirmed_at": "",
                "continuation_consumed_candle": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        sources[source] = state
        payload["sources"] = sources
        _write_runtime_state(payload)


def mark_model24_initial_target_armed(
    source_model: object,
    trend_side: object,
    target_price: object,
    target_time: object,
    candle_time: object,
) -> None:
    """Arma uma unica CONTINUATION no TP aceito da INITIAL."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    try:
        target = float(target_price)
    except (TypeError, ValueError):
        return
    if side not in {"BUY", "SELL"} or target <= 0.0:
        return
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        already_consumed = bool(
            str(state.get("continuation_status") or "") == "CONSUMED"
            and str(state.get("continuation_side") or "").upper() == side
        )
        if already_consumed:
            return
        state.update(
            {
                "continuation_status": "WAITING_INITIAL_TARGET_TRIGGER",
                "continuation_origin_role": "INITIAL",
                "continuation_side": side,
                "continuation_target_price": target,
                "continuation_target_time": str(target_time or "N/D"),
                "continuation_armed_candle": str(candle_time or "N/D"),
                "continuation_armed_at": datetime.now(timezone.utc).isoformat(),
                "continuation_consumed_candle": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        sources[source] = state
        payload["sources"] = sources
        _write_runtime_state(payload)


def model24_continuation_watch(source_model: object) -> dict[str, Any]:
    """Retorna uma copia do watch de TP que pode liberar CONTINUATION."""
    source = _model24_source_key(source_model)
    with _LOCK:
        payload = _load_runtime_state()
        state = dict(dict(payload.get("sources") or {}).get(source) or {})
    status = str(state.get("continuation_status") or "")
    if status != "WAITING_INITIAL_TARGET_TRIGGER":
        return {}
    side = str(state.get("continuation_side") or "").upper()
    try:
        target = float(state.get("continuation_target_price") or 0.0)
    except (TypeError, ValueError):
        return {}
    if side not in {"BUY", "SELL"} or target <= 0.0:
        return {}
    return {
        "side": side,
        "target_price": target,
        "target_time": str(state.get("continuation_target_time") or "N/D"),
        "armed_candle": str(state.get("continuation_armed_candle") or "N/D"),
        "armed_at": str(state.get("continuation_armed_at") or ""),
        "origin_role": "INITIAL",
        "target_exit_confirmed": False,
    }


def mark_model24_continuation_target_exit_confirmed(
    source_model: object,
    trend_side: object,
    target_price: object,
) -> None:
    """Persiste a confirmacao do TP para nao repetir consultas ao historico."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    try:
        target = float(target_price)
    except (TypeError, ValueError):
        return
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        try:
            armed_target = float(state.get("continuation_target_price") or 0.0)
        except (TypeError, ValueError):
            return
        if (
            str(state.get("continuation_status") or "")
            != "WAITING_REENTRY_TARGET_EXIT"
            or str(state.get("continuation_side") or "").upper() != side
            or abs(armed_target - target) > 1e-9
        ):
            return
        state.update(
            {
                "continuation_status": "REENTRY_TARGET_EXIT_CONFIRMED",
                "continuation_target_exit_confirmed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        sources[source] = state
        payload["sources"] = sources
        _write_runtime_state(payload)


def mark_model24_continuation_accepted(
    source_model: object,
    trend_side: object,
    candle_time: object,
) -> None:
    """Consome o watch somente depois do aceite da CONTINUATION a mercado."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        state.update(
            {
                "continuation_status": "CONSUMED",
                "continuation_side": side,
                "continuation_consumed_candle": str(candle_time or "N/D"),
                "continuation_consumed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        sources[source] = state
        payload["sources"] = sources
        _write_runtime_state(payload)


@dataclass(frozen=True)
class Model24ReentryGateDecision:
    allowed: bool
    status: str
    reason: str
    blocked_opportunity_key: str = ""


def mark_model24_extreme_full_exit(
    source_model: object,
    trend_side: object,
    exit_status: object,
    candle_time: object,
) -> None:
    """Registra o Full Exit extremo sem bloquear a proxima reentrada."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    event_key = f"{side}|{str(exit_status or '').upper()}|{candle_time or 'N/D'}"
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        if str(state.get("last_extreme_exit_event_key") or "") != event_key:
            state.update(
                {
                    "trend_side": side,
                    "initial_consumed": True,
                    "skip_first_reentry_after_extreme": False,
                    "blocked_reentry_opportunity_key": "",
                    "released_reentry_opportunity_key": "",
                    "last_extreme_exit_event_key": event_key,
                    "last_extreme_exit_status": str(exit_status or "").upper(),
                    "last_extreme_exit_candle": str(candle_time or "N/D"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            sources[source] = state
            payload["sources"] = sources
            _write_runtime_state(payload)


def evaluate_model24_reentry_opportunity(
    source_model: object,
    trend_side: object,
    opportunity_key: object,
) -> Model24ReentryGateDecision:
    """Libera toda reentrada valida; a antiga regra de descarte foi removida."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    key = str(opportunity_key or "").strip()
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        if bool(state.get("skip_first_reentry_after_extreme")):
            state.update(
                {
                    "skip_first_reentry_after_extreme": False,
                    "blocked_reentry_opportunity_key": "",
                    "released_reentry_opportunity_key": key,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            sources[source] = state
            payload["sources"] = sources
            _write_runtime_state(payload)
        return Model24ReentryGateDecision(
            allowed=True,
            status="M24_REENTRY_LIBERADA_SEM_DESCARTE_POS_EXTREMO",
            reason=(
                "Reentrada valida liberada; nao existe descarte automatico da "
                "primeira oportunidade apos Full Exit RSI 70/30."
            ),
        )


def _model24_source_key(value: object) -> str:
    if is_model24(value):
        return MODEL_24_RUNTIME_SOURCE
    number = operational_model_number(value)
    if number not in MODEL_24_LEGACY_SOURCE_MODEL_NUMBERS:
        raise ValueError("Identidade M24 invalida para o estado operacional.")
    # Chamadas legadas convergem para o mesmo estado autonomo. Isso impede que
    # sete rotas equivalentes consumam ou liberem entradas separadamente.
    return MODEL_24_RUNTIME_SOURCE


def _write_runtime_state(payload: dict[str, Any]) -> None:
    versioned_payload = dict(payload)
    versioned_payload.update(
        {
            "setup_contract_version": MODEL_24_SETUP_CONTRACT_VERSION,
            "setup_contract_fingerprint": MODEL_24_SETUP_CONTRACT_FINGERPRINT,
        }
    )
    _atomic_json_write(MODEL_24_RUNTIME_STATE_PATH, versioned_payload)


def _load_runtime_state() -> dict[str, Any]:
    try:
        payload = json.loads(MODEL_24_RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized = dict(payload)
    needs_rewrite = (
        str(normalized.get("setup_contract_version") or "")
        != MODEL_24_SETUP_CONTRACT_VERSION
        or str(normalized.get("setup_contract_fingerprint") or "")
        != MODEL_24_SETUP_CONTRACT_FINGERPRINT
    )
    sources = dict(normalized.get("sources") or {})
    if MODEL_24_RUNTIME_SOURCE not in sources:
        latest_state: dict[str, Any] = {}
        latest_updated_at = ""
        for legacy_key, legacy_value in sources.items():
            if str(legacy_key).upper() not in {
                f"M{number}" for number in MODEL_24_LEGACY_SOURCE_MODEL_NUMBERS
            }:
                continue
            candidate = dict(legacy_value or {})
            candidate_updated_at = str(candidate.get("updated_at") or "")
            if candidate_updated_at >= latest_updated_at:
                latest_state = candidate
                latest_updated_at = candidate_updated_at
        if latest_state:
            sources[MODEL_24_RUNTIME_SOURCE] = latest_state
            needs_rewrite = True
    # Estados antigos podem conter ``<memory at 0x...>`` quando um registro
    # numpy/MT5 teve o atributo ``.data`` confundido com a data do candle.
    # Elimina identidades volateis e remove a trava de reentrada aposentada.
    for source_key, source_value in tuple(sources.items()):
        state = dict(source_value or {})
        extreme_candle = str(state.get("last_extreme_exit_candle") or "")
        if extreme_candle.startswith("<memory at "):
            side = str(state.get("trend_side") or "").upper()
            status = str(state.get("last_extreme_exit_status") or "").upper()
            state["last_extreme_exit_candle"] = "N/D"
            state["last_extreme_exit_event_key"] = f"{side}|{status}|N/D"
            needs_rewrite = True
        for field_name in ("last_entry_candle",):
            if str(state.get(field_name) or "").startswith("<memory at "):
                state[field_name] = "N/D"
                needs_rewrite = True
        blocked_key = str(state.get("blocked_reentry_opportunity_key") or "")
        if "<memory at " in blocked_key:
            state["blocked_reentry_opportunity_key"] = ""
            needs_rewrite = True
        if not MODEL_24_SETUP.skip_first_reentry_after_extreme and bool(
            state.get("skip_first_reentry_after_extreme")
        ):
            state["skip_first_reentry_after_extreme"] = False
            state["blocked_reentry_opportunity_key"] = ""
            state["released_reentry_opportunity_key"] = ""
            needs_rewrite = True
        sources[source_key] = state
    if str(normalized.get("last_initial_candle") or "").startswith("<memory at "):
        normalized["last_initial_candle"] = "N/D"
        needs_rewrite = True
    normalized["sources"] = sources
    normalized["setup_contract_version"] = MODEL_24_SETUP_CONTRACT_VERSION
    normalized["setup_contract_fingerprint"] = (
        MODEL_24_SETUP_CONTRACT_FINGERPRINT
    )
    if needs_rewrite:
        try:
            _write_runtime_state(normalized)
        except OSError:
            # A decisao usa imediatamente o estado sanitizado mesmo se o
            # Windows/OneDrive bloquear transitoriamente a persistencia.
            pass
    return normalized


def _model24_last_initial_side(payload: dict[str, Any]) -> str:
    side = str(payload.get("last_initial_side") or "").upper()
    if side in {"BUY", "SELL"}:
        return side
    # Migra em leitura o estado legado: o registro mais recente entre as fontes
    # representa a ultima INITIAL aceita antes da criacao do marcador global.
    latest_side = ""
    latest_updated_at = ""
    for state_value in dict(payload.get("sources") or {}).values():
        state = dict(state_value or {})
        candidate_side = str(state.get("trend_side") or "").upper()
        candidate_updated_at = str(state.get("updated_at") or "")
        if candidate_side in {"BUY", "SELL"} and candidate_updated_at >= latest_updated_at:
            latest_side = candidate_side
            latest_updated_at = candidate_updated_at
    return latest_side


@dataclass(frozen=True)
class Model24EntryDecision:
    direction: str = "WAIT"
    status: str = "M24_AGUARDA_RSI50"
    reason: str = "Aguardando novos cruzamentos do preco/SMA20 e RSI14/50."
    closed_candle_time: str = "N/D"
    last_price: float | None = None
    entry_price: float | None = None
    initial_stop: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    atr14: float | None = None
    distance_atr: float | None = None
    rsi14: float | None = None
    previous_rsi14: float | None = None
    micro_swing_price: float | None = None
    micro_swing_time: str = "N/D"
    structural_target_price: float | None = None
    structural_target_time: str = "N/D"
    price_cross_time: str = "N/D"
    rsi_cross_time: str = "N/D"
    entry_order_type: str = "NONE"

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
            and self.status.endswith("_PRONTA")
        )


@dataclass(frozen=True)
class Model24LateralizationDecision:
    """Reposicionamento do range sobre uma REENTRY que continua aberta."""

    ready: bool = False
    status: str = "M24_LATERALIZATION_AGUARDA_RETORNO"
    reason: str = "Aguardando falha do TP Fibonacci e retorno confirmado ao range."
    target_price: float | None = None
    stop_price: float | None = None
    pivot_time: str = "N/D"


def evaluate_model24_lateralization(
    candles: Iterable[object],
    *,
    side: object,
    entry_price: float,
    current_price: float,
    current_stop: float,
    fibonacci_target: float,
) -> Model24LateralizationDecision:
    """Converte uma REENTRY aberta em gestao de range, sem adicionar volume."""
    if not MODEL_24_SETUP.lateralization_enabled:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_DESLIGADA",
            reason="A rota de lateralizacao esta desligada no contrato M24.",
        )
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"}:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_LADO_INVALIDO",
            reason="Lateralizacao exige uma REENTRY BUY ou SELL aberta.",
        )
    rows = list(candles or ())[-MODEL_24_SETUP.raw_candles:]
    if len(rows) < 4:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_CANDLES_INSUFICIENTES",
            reason="Lateralizacao aguarda microestrutura M5 fechada suficiente.",
        )
    closed = rows[:-1]
    target, pivot_time = _model24_reentry_structural_target(
        closed,
        normalized,
        float(entry_price),
        maximum_age=MODEL_24_SETUP.reentry_micro_pivot_maximum_age,
    )
    if target is None:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_AGUARDA_MICRO_EXTREMO",
            reason=(
                "TP Fibonacci ainda nao convertido: aguarda microtopo no BUY "
                "ou microfundo no SELL confirmado 1+1."
            ),
        )
    current = float(current_price)
    original_target = float(fibonacci_target or 0.0)
    candidate_target = float(target)
    target_is_executable = (
        current < candidate_target < original_target
        if normalized == "BUY"
        else original_target < candidate_target < current
    )
    if original_target <= 0.0 or not target_is_executable:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_AGUARDA_RETORNO",
            reason=(
                "O microextremo ainda nao forma um alvo de range mais proximo "
                "e executavel que o TP Fibonacci original."
            ),
            target_price=candidate_target,
            pivot_time=pivot_time,
        )
    reward = (
        candidate_target - float(entry_price)
        if normalized == "BUY"
        else float(entry_price) - candidate_target
    )
    if reward <= 0.0:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_RANGE_INVALIDO",
            reason="O range confirmado nao oferece ganho positivo desde a entrada.",
            target_price=candidate_target,
            pivot_time=pivot_time,
        )
    risk = reward / MODEL_24_SETUP.lateralization_risk_reward
    rr_stop = (
        float(entry_price) - risk
        if normalized == "BUY"
        else float(entry_price) + risk
    )
    existing_stop = float(current_stop or 0.0)
    stop = rr_stop
    if existing_stop > 0.0:
        stop = (
            max(existing_stop, rr_stop)
            if normalized == "BUY"
            else min(existing_stop, rr_stop)
        )
    stop_is_executable = stop < current if normalized == "BUY" else stop > current
    if not stop_is_executable:
        return Model24LateralizationDecision(
            status="M24_LATERALIZATION_SL_RR3_INVALIDO",
            reason=(
                "O SL RR 3:1 ficaria no lado invalido do preco atual; manter "
                "SL/TP atuais e aguardar novo range."
            ),
            target_price=candidate_target,
            stop_price=stop,
            pivot_time=pivot_time,
        )
    return Model24LateralizationDecision(
        ready=True,
        status=f"M24_LATERALIZATION_{normalized}_RANGE_PRONTO",
        reason=(
            f"REENTRY {normalized} permaneceu aberta, falhou o TP Fibonacci e "
            "retornou ao range. Reposicionar TP no fechamento do microextremo "
            f"anterior e SL em RR {MODEL_24_SETUP.lateralization_risk_reward:.0f}:1, "
            "sem nova ordem e sem afrouxar o SL atual."
        ),
        target_price=round(candidate_target, 2),
        stop_price=round(stop, 2),
        pivot_time=pivot_time,
    )


def evaluate_model24_rsi50_market_entry(
    candles: Iterable[object],
    *,
    entry_role: str = "INITIAL",
    pip_size: float = MODEL_24_PIP_SIZE,
    require_rsi_cross: bool = MODEL_24_SETUP.initial_requires_rsi_cross,
) -> Model24EntryDecision:
    """Avalia os cruzamentos novos de preco/SMA20 e RSI50 da entrada inicial."""
    rows = list(candles or ())[-MODEL_24_SETUP.raw_candles:]
    normalized_role = str(entry_role or "INITIAL").upper()
    if normalized_role == "REENTRY":
        return evaluate_model24_pending_reentry(rows, pip_size=pip_size)
    if len(rows) < MODEL_24_SETUP.raw_candles:
        return Model24EntryDecision(
            status=(
                f"M24_AQUECENDO_{len(rows)}_DE_"
                f"{MODEL_24_SETUP.raw_candles}_CANDLES"
            ),
            reason=(
                f"M24 exige {MODEL_24_SETUP.closed_candles} candles M5 fechados "
                "e o candle atual em formacao."
            ),
        )
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if any(value is None for value in closes):
        return Model24EntryDecision(
            status="M24_DADOS_INVALIDOS",
            reason="Candle M5 fechado sem preco de fechamento valido.",
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, MODEL_24_SETUP.sma_fast_period)
    sma50 = _sma(values, MODEL_24_SETUP.sma_slow_period)
    atr14 = _model24_atr(closed)
    distance_atr = _model24_distance_atr(sma20, sma50, atr14)
    cross_side, price_cross_index, rsi_cross_index, rsi_values = (
        _model24_initial_cross_confirmation(
            values,
            require_rsi_cross=require_rsi_cross,
        )
    )
    rsi14 = rsi_values[-1]
    previous_rsi14 = rsi_values[-2]
    common = {
        "closed_candle_time": _time(closed[-1]),
        "last_price": values[-1],
        "sma20": sma20,
        "sma50": sma50,
        "atr14": atr14,
        "distance_atr": distance_atr,
        "rsi14": rsi14,
        "previous_rsi14": previous_rsi14,
        "price_cross_time": (
            _time(closed[price_cross_index])
            if price_cross_index is not None
            else "N/D"
        ),
        "rsi_cross_time": (
            _time(closed[rsi_cross_index])
            if rsi_cross_index is not None
            else "N/D"
        ),
    }
    if (
        MODEL_24_SETUP.distance_atr_filter_enabled
        and distance_atr < MODEL_24_DISTANCE_ATR_MIN
    ):
        return Model24EntryDecision(
            status="M24_DISTANCE_ATR_BLOQUEADO",
            reason=(
                f"M24 exige distancia absoluta entre SMA20/SMA50 de pelo menos "
                f"{MODEL_24_DISTANCE_ATR_MIN:.2f} ATR; atual={distance_atr:.4f}. "
                "A posicao relativa das medias nao define a direcao."
            ),
            **common,
        )
    if cross_side not in {"BUY", "SELL"}:
        return Model24EntryDecision(
            status="M24_INITIAL_AGUARDA_CRUZAMENTOS_PRECO_SMA20_E_RSI50",
            reason=(
                "Entrada inicial exige novo cruzamento do preco na SMA20 e "
                "novo cruzamento do RSI14 em 50 na mesma direcao. Podem "
                "ocorrer em candles M5 diferentes, mas ambos devem existir "
                "e permanecer validos."
            ),
            **common,
        )
    side = cross_side
    entry = float(values[-1])
    cross_candle = closed[int(price_cross_index)]
    stop_reference = _number(
        cross_candle,
        "low" if side == "BUY" else "high",
    )
    stop_reference_time = _time(cross_candle)
    stop_reference_label = "candle M5 que cruzou a SMA20"
    if stop_reference is None:
        return Model24EntryDecision(
            direction="WAIT",
            status="M24_INITIAL_SEM_EXTREMO_DA_VELA_DE_CRUZAMENTO_PARA_SL",
            reason=(
                "A entrada inicial aguarda a minima/maxima valida do candle "
                "M5 que cruzou a SMA20 para posicionar o SL."
            ),
            entry_price=entry,
            **common,
        )
    normalized_pip_size = max(float(pip_size or MODEL_24_PIP_SIZE), 0.0)
    stop = (
        float(stop_reference) - normalized_pip_size
        if side == "BUY"
        else float(stop_reference) + normalized_pip_size
    )
    valid = stop < entry if side == "BUY" else stop > entry
    if not valid:
        return Model24EntryDecision(
            direction="WAIT",
            status="M24_STOP_INICIAL_INVALIDO",
            reason=(
                "A extremidade do candle M5 que cruzou a SMA20 nao produz SL "
                "valido para a entrada inicial."
            ),
            entry_price=entry,
            initial_stop=stop,
            micro_swing_price=float(stop_reference),
            micro_swing_time=stop_reference_time,
            **common,
        )
    fibonacci_target, fibonacci_anchor_time = _model24_initial_fibonacci_target(
        closed,
        side,
        entry,
    )
    if fibonacci_target is None:
        return Model24EntryDecision(
            direction="WAIT",
            status="M24_INITIAL_AGUARDA_PROJECAO_FIBONACCI_100_VALIDA",
            reason=(
                "A entrada inicial aguarda uma perna estrutural completa anterior "
                "na mesma direcao para projetar o TP Fibonacci de 100%."
            ),
            entry_price=entry,
            initial_stop=stop,
            micro_swing_price=float(stop_reference),
            micro_swing_time=stop_reference_time,
            **common,
        )
    return Model24EntryDecision(
        direction=side,
        status=f"M24_INITIAL_{side}_PRECO_SMA20_RSI50_MERCADO_PRONTA",
        reason=(
            f"{side} inicial a mercado: preco cruzou a SMA20 e o RSI14 cruzou "
            f"50 na mesma direcao; eventos nao simultaneos foram mantidos "
            f"validos. SL um pip alem do "
            f"{stop_reference_label}. TP pela projecao Fibonacci de 100% da "
            "perna estrutural anterior."
        ),
        entry_price=entry,
        initial_stop=stop,
        micro_swing_price=float(stop_reference),
        micro_swing_time=stop_reference_time,
        structural_target_price=fibonacci_target,
        structural_target_time=fibonacci_anchor_time,
        entry_order_type="MARKET",
        **common,
    )


def evaluate_model24_pending_reentry(
    candles: Iterable[object],
    *,
    pip_size: float = MODEL_24_PIP_SIZE,
) -> Model24EntryDecision:
    """Reentrada que acompanha cada M5 depois de uma correcao confirmada."""
    rows = list(candles or ())[-MODEL_24_SETUP.raw_candles:]
    if len(rows) < MODEL_24_SETUP.raw_candles:
        return Model24EntryDecision(
            status=(
                f"M24_AQUECENDO_{len(rows)}_DE_"
                f"{MODEL_24_SETUP.raw_candles}_CANDLES"
            ),
            reason=(
                f"M24 exige {MODEL_24_SETUP.closed_candles} candles M5 fechados "
                "e o candle atual em formacao."
            ),
        )
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if any(value is None for value in closes):
        return Model24EntryDecision(
            status="M24_DADOS_INVALIDOS",
            reason="Candle M5 fechado sem preco de fechamento valido.",
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, MODEL_24_SETUP.sma_fast_period)
    sma50 = _sma(values, MODEL_24_SETUP.sma_slow_period)
    atr14 = _model24_atr(closed)
    distance_atr = _model24_distance_atr(sma20, sma50, atr14)
    rsi14 = _wilder_rsi(values, MODEL_24_SETUP.rsi_period)
    previous_rsi14 = _wilder_rsi(values[:-1], MODEL_24_SETUP.rsi_period)
    common = {
        "closed_candle_time": _time(closed[-1]),
        "last_price": values[-1],
        "sma20": sma20,
        "sma50": sma50,
        "atr14": atr14,
        "distance_atr": distance_atr,
        "rsi14": rsi14,
        "previous_rsi14": previous_rsi14,
    }
    if (
        MODEL_24_SETUP.distance_atr_filter_enabled
        and distance_atr < MODEL_24_DISTANCE_ATR_MIN
    ):
        return Model24EntryDecision(
            status="M24_DISTANCE_ATR_BLOQUEADO",
            reason=(
                f"M24 exige distancia absoluta entre SMA20/SMA50 de pelo menos "
                f"{MODEL_24_DISTANCE_ATR_MIN:.2f} ATR; atual={distance_atr:.4f}. "
                "A posicao relativa das medias nao define a direcao."
            ),
            **common,
        )
    if values[-1] > sma20:
        side = "BUY"
        trigger = _number(closed[-1], "high")
        order_type = "BUY_STOP"
    elif values[-1] < sma20:
        side = "SELL"
        trigger = _number(closed[-1], "low")
        order_type = "SELL_STOP"
    else:
        return Model24EntryDecision(
            status="M24_REENTRY_AGUARDA_DIRECAO_FORA_DA_SMA20",
            reason=(
                "Reentrada aguarda o ultimo M5 fechar de um lado definido da SMA20."
            ),
            **common,
        )
    correction_rows = closed[-MODEL_24_SETUP.reentry_correction_lookback :]
    correction_found = False
    for index, row in enumerate(
        correction_rows,
        start=len(closed) - len(correction_rows),
    ):
        if index + 1 < MODEL_24_SETUP.sma_fast_period:
            continue
        candle_sma20 = _sma(values[: index + 1], MODEL_24_SETUP.sma_fast_period)
        low = _number(row, "low")
        high = _number(row, "high")
        if low is not None and high is not None and float(low) <= candle_sma20 <= float(high):
            correction_found = True
            break
    if not correction_found:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_AGUARDA_RETORNO_A_SMA20",
            reason=(
                "Reentrada aguarda o preco retornar/tocar a SMA20 em um dos "
                "cinco ultimos M5 fechados antes da retomada."
            ),
            **common,
        )
    trigger = float(trigger or 0.0)
    live_price = _number(rows[-1], "close")
    already_crossed = bool(
        live_price is not None
        and (
            float(live_price) >= trigger
            if side == "BUY"
            else float(live_price) <= trigger
        )
    )
    entry = float(live_price) if already_crossed else trigger
    order_type = "MARKET" if already_crossed else order_type
    micro_swing, micro_swing_time = _latest_micro_swing(
        closed,
        side,
        maximum_age=MODEL_24_SETUP.reentry_micro_pivot_maximum_age,
    )
    if micro_swing is None:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_AGUARDA_MICRO_PIVO_1X1",
            reason=(
                "Reentrada aguarda microfundo/microtopo M5 confirmado 1+1 "
                "para definir o SL."
            ),
            **common,
        )
    normalized_pip_size = max(float(pip_size or MODEL_24_PIP_SIZE), 0.0)
    stop = (
        float(micro_swing) - normalized_pip_size
        if side == "BUY"
        else float(micro_swing) + normalized_pip_size
    )
    valid = stop < entry if side == "BUY" else stop > entry
    if not valid:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_STOP_MICRO_PIVO_INVALIDO",
            reason="Extremo oposto da ultima vela M5 nao produz SL valido.",
            entry_price=entry,
            initial_stop=stop,
            micro_swing_price=float(micro_swing),
            micro_swing_time=micro_swing_time,
            **common,
        )
    structural_target, structural_target_time = _model24_initial_fibonacci_target(
        closed,
        side,
        entry,
    )
    if structural_target is None:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_AGUARDA_ALVO_ESTRUTURAL_VALIDO",
            reason=(
                "Reentrada aguarda perna estrutural anterior valida para projetar "
                "o TP Fibonacci de 100%."
            ),
            entry_price=entry,
            initial_stop=stop,
            micro_swing_price=float(micro_swing),
            micro_swing_time=micro_swing_time,
            **common,
        )
    return Model24EntryDecision(
        direction=side,
        status=f"M24_REENTRY_{side}_{order_type}_SMA20_PRONTA",
        reason=(
            f"Reentrada {order_type}: retorno a SMA20 confirmado e retomada no "
            "rompimento do extremo do M5 anterior; se o preco ja ultrapassou o "
            "gatilho, entrada a mercado. SL um pip alem do microfundo/microtopo "
            "1+1 mais proximo e TP Fibonacci 100% da perna anterior."
        ),
        entry_price=entry,
        initial_stop=stop,
        micro_swing_price=float(micro_swing),
        micro_swing_time=micro_swing_time,
        structural_target_price=structural_target,
        structural_target_time=structural_target_time,
        entry_order_type=order_type,
        **common,
    )


def evaluate_model24_continuation(
    candles: Iterable[object],
    *,
    watch: dict[str, Any] | None,
    target_exit_confirmed: bool,
    pip_size: float = MODEL_24_PIP_SIZE,
) -> Model24EntryDecision:
    """Arma CONTINUATION Stop logo alem do TP Fibonacci da INITIAL."""
    rows = list(candles or ())[-MODEL_24_SETUP.raw_candles:]
    if not MODEL_24_SETUP.continuation_enabled or not watch:
        return Model24EntryDecision(
            status="M24_CONTINUATION_SEM_TP_ARMADO",
            reason="CONTINUATION aguarda uma INITIAL aceita com TP Fibonacci.",
        )
    if len(rows) < MODEL_24_SETUP.raw_candles:
        return Model24EntryDecision(
            status=f"M24_CONTINUATION_AQUECENDO_{len(rows)}_CANDLES",
            reason="CONTINUATION aguarda a janela M5 operacional completa.",
        )
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if any(value is None for value in closes):
        return Model24EntryDecision(
            status="M24_CONTINUATION_DADOS_INVALIDOS",
            reason="CONTINUATION recebeu candle M5 sem fechamento valido.",
        )
    side = str(watch.get("side") or "").upper()
    try:
        target = float(watch.get("target_price") or 0.0)
    except (TypeError, ValueError):
        target = 0.0
    values = [float(value) for value in closes if value is not None]
    current_close = values[-1]
    rsi14 = _wilder_rsi(values, MODEL_24_SETUP.rsi_period)
    previous_rsi14 = _wilder_rsi(values[:-1], MODEL_24_SETUP.rsi_period)
    closed_time = _time(closed[-1])
    common = {
        "closed_candle_time": closed_time,
        "last_price": current_close,
        "rsi14": rsi14,
        "previous_rsi14": previous_rsi14,
        "sma20": _sma(values, MODEL_24_SETUP.sma_fast_period),
        "sma50": _sma(values, MODEL_24_SETUP.sma_slow_period),
        "atr14": _model24_atr(closed),
    }
    if side not in {"BUY", "SELL"} or target <= 0.0:
        return Model24EntryDecision(
            status="M24_CONTINUATION_WATCH_INVALIDO",
            reason="CONTINUATION sem lado ou alvo estrutural auditavel.",
            **common,
        )
    del target_exit_confirmed
    previous_closed_candle = closed[-1]
    stop_reference = _number(
        previous_closed_candle,
        "low" if side == "BUY" else "high",
    )
    stop_reference_time = closed_time
    if stop_reference is None or float(stop_reference) <= 0.0:
        return Model24EntryDecision(
            direction=side,
            status="M24_CONTINUATION_AGUARDA_EXTREMO_CANDLE_ANTERIOR",
            reason=(
                "CONTINUATION aguarda fundo/topo valido no ultimo M5 fechado."
            ),
            **common,
        )
    stop = float(stop_reference)
    normalized_pip_size = max(float(pip_size or MODEL_24_PIP_SIZE), 0.0)
    trigger = (
        target + normalized_pip_size
        if side == "BUY"
        else target - normalized_pip_size
    )
    valid = stop < trigger if side == "BUY" else stop > trigger
    if not valid:
        return Model24EntryDecision(
            direction=side,
            status="M24_CONTINUATION_STOP_INVALIDO",
            reason=(
                "O fundo/topo do ultimo M5 fechado nao produz SL valido para "
                "a CONTINUATION."
            ),
            entry_price=trigger,
            initial_stop=stop,
            micro_swing_price=float(stop_reference),
            micro_swing_time=stop_reference_time,
            **common,
        )
    return Model24EntryDecision(
        direction=side,
        status=f"M24_CONTINUATION_{side}_STOP_NO_TP_INITIAL_PRONTA",
        reason=(
            f"CONTINUATION {side}_STOP armada um pip alem do TP Fibonacci "
            f"da INITIAL ({target:.2f}) para ativar somente depois do alvo; "
            "sem TP proprio, com SL no extremo do ultimo M5 fechado."
        ),
        entry_price=trigger,
        initial_stop=stop,
        micro_swing_price=float(stop_reference),
        micro_swing_time=stop_reference_time,
        entry_order_type="BUY_STOP" if side == "BUY" else "SELL_STOP",
        **common,
    )


def model24_previous_candle_stop(
    candles: Iterable[object], side: object
) -> tuple[float | None, str]:
    """SL móvel no extremo do ultimo M5 fechado; o chamador impede afrouxamento."""
    rows = list(candles or ())
    if len(rows) < 2:
        return None, "N/D"
    closed = rows[-2]
    normalized = str(side or "").upper()
    field = "low" if normalized == "BUY" else "high" if normalized == "SELL" else ""
    return (_number(closed, field), _time(closed)) if field else (None, "N/D")


def model24_sma20_trailing_stop(
    candles: Iterable[object], side: object
) -> tuple[float | None, str]:
    """Retorna a SMA20 do último M5 fechado para trailing monotônico."""
    rows = list(candles or ())[-MODEL_24_SETUP.raw_candles:]
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"} or len(rows) < 21:
        return None, "N/D"
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if len(closes) < MODEL_24_SETUP.sma_fast_period or any(
        value is None for value in closes
    ):
        return None, "N/D"
    values = [float(value) for value in closes if value is not None]
    return _sma(values, MODEL_24_SETUP.sma_fast_period), _time(closed[-1])


def model24_micro_pivot_stop(
    candles: Iterable[object],
    side: object,
    *,
    maximum_age: int = 5,
) -> tuple[float | None, str]:
    """Retorna o micro pivo 1+1 confirmado mais recente para proteger o M24."""
    rows = list(candles or ())
    if len(rows) < 4:
        return None, "N/D"
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"}:
        return None, "N/D"
    # O ultimo elemento e a vela atual; somente velas fechadas confirmam o 1+1.
    return _latest_micro_swing(
        rows[:-1],
        normalized,
        maximum_age=max(1, int(maximum_age)),
    )


def model24_initial_structure_trailing_stop(
    candles: Iterable[object],
    side: object,
    *,
    entry_candle_time: object = None,
) -> tuple[float | None, str]:
    """Protege INITIAL por microestrutura formada depois da abertura."""
    rows = list(candles or ())
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"} or len(rows) < 7:
        return None, "N/D"
    closed = rows[:-1]
    last_index = len(closed) - 1
    highs = [_number(row, "high") for row in closed]
    lows = [_number(row, "low") for row in closed]
    if any(value is None for value in highs + lows):
        return None, "N/D"
    parsed_highs = [float(value) for value in highs if value is not None]
    parsed_lows = [float(value) for value in lows if value is not None]
    entry_timestamp = _timestamp(entry_candle_time)

    def formed_after_entry(index: int) -> bool:
        if entry_timestamp is None:
            return True
        candle_timestamp = _timestamp(_time(closed[index]))
        return candle_timestamp is not None and candle_timestamp > entry_timestamp

    high_pivots = [
        index
        for index in range(1, last_index)
        if parsed_highs[index] > parsed_highs[index - 1]
        and parsed_highs[index] >= parsed_highs[index + 1]
        and formed_after_entry(index)
    ]
    low_pivots = [
        index
        for index in range(1, last_index)
        if parsed_lows[index] < parsed_lows[index - 1]
        and parsed_lows[index] <= parsed_lows[index + 1]
        and formed_after_entry(index)
    ]

    if normalized == "BUY":
        for top_index in reversed(high_pivots):
            created_bottoms = [
                index for index in low_pivots if top_index < index < last_index
            ]
            if created_bottoms and parsed_highs[last_index] > parsed_highs[top_index]:
                bottom_index = created_bottoms[-1]
                return parsed_lows[bottom_index], _time(closed[bottom_index])
    else:
        for bottom_index in reversed(low_pivots):
            created_tops = [
                index for index in high_pivots if bottom_index < index < last_index
            ]
            if created_tops and parsed_lows[last_index] < parsed_lows[bottom_index]:
                top_index = created_tops[-1]
                return parsed_highs[top_index], _time(closed[top_index])
    return None, "N/D"


def model24_sma20_stop_after_two_closes(
    candles: Iterable[object],
    side: object,
) -> tuple[float | None, str]:
    """Libera a SMA20 como SL apos dois fechamentos favoraveis consecutivos."""
    rows = list(candles or ())
    normalized = str(side or "").upper()
    minimum_rows = MODEL_24_SETUP.sma_fast_period + 2
    if normalized not in {"BUY", "SELL"} or len(rows) < minimum_rows:
        return None, "N/D"
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    minimum_closed = MODEL_24_SETUP.sma_fast_period + 1
    if len(closes) < minimum_closed or any(
        value is None for value in closes[-minimum_closed:]
    ):
        return None, "N/D"
    values = [float(value) for value in closes if value is not None]
    previous_sma20 = _sma(values[:-1], MODEL_24_SETUP.sma_fast_period)
    current_sma20 = _sma(values, MODEL_24_SETUP.sma_fast_period)
    previous_close = values[-2]
    current_close = values[-1]
    confirmed = (
        previous_close > previous_sma20 and current_close > current_sma20
        if normalized == "BUY"
        else previous_close < previous_sma20 and current_close < current_sma20
    )
    if not confirmed:
        return None, _time(closed[-1])
    return float(current_sma20), _time(closed[-1])


@dataclass(frozen=True)
class Model24BasketSnapshot:
    status: str = "WAITING_NEW_ROUND"
    round_id: str = ""
    positions: int = 0
    net_result_usd: float = 0.0
    exit_reason: str = ""
    closed: int = 0
    rejected: int = 0
    updated_at: str = ""


@dataclass
class Model24BasketManager:
    execution_service: Model24ExecutionPort
    state_path: Path = field(default_factory=lambda: MODEL_24_STATE_PATH)
    audit_path: Path = field(default_factory=lambda: MODEL_24_AUDIT_PATH)
    full_exit_usd: float = MODEL_24_FULL_EXIT_USD

    def evaluate_once(self) -> Model24BasketSnapshot:
        with _LOCK:
            positions = [
                position
                for position in self.execution_service.list_open_positions()
                if model24_position_matches(position)
            ]
            now = datetime.now(timezone.utc).isoformat()
            if not positions:
                snapshot = Model24BasketSnapshot(updated_at=now)
                self._write(snapshot)
                return snapshot
            net = round(sum(model24_position_net(position) for position in positions), 2)
            if net < self.full_exit_usd:
                snapshot = Model24BasketSnapshot(
                    status="ACCUMULATING",
                    round_id=self._round_id(),
                    positions=len(positions),
                    net_result_usd=net,
                    updated_at=now,
                )
                self._write(snapshot)
                return snapshot
            results: list[dict[str, Any]] = []
            reason = "M24_FULL_EXIT_PLUS_1000_USD"
            for position in positions:
                side = "BUY" if int(getattr(position, "type", -1) or 0) == 0 else "SELL"
                response = self.execution_service.close_position(
                    symbol=str(getattr(position, "symbol", "") or "").upper(),
                    ticket=int(getattr(position, "ticket", 0) or 0),
                    side=side,
                    volume=float(getattr(position, "volume", 0.0) or 0.0),
                    reason=reason,
                )
                results.append(
                    {
                        "ticket": int(getattr(position, "ticket", 0) or 0),
                        "accepted": bool(getattr(response, "accepted", False)),
                        "message": str(getattr(response, "message", "") or ""),
                    }
                )
            closed = sum(bool(item["accepted"]) for item in results)
            snapshot = Model24BasketSnapshot(
                status="EXIT_SUBMITTED" if closed == len(results) else "EXIT_PARTIAL",
                round_id=self._round_id(),
                positions=len(positions),
                net_result_usd=net,
                exit_reason=reason,
                closed=closed,
                rejected=len(results) - closed,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._write(snapshot)
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({**asdict(snapshot), "results": results}) + "\n")
            return snapshot

    def _round_id(self) -> str:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            existing = str(payload.get("round_id") or "")
            if existing:
                return existing
        except (OSError, ValueError, TypeError):
            pass
        return "M24-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]

    def _write(self, snapshot: Model24BasketSnapshot) -> None:
        _atomic_json_write(self.state_path, asdict(snapshot))


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    """Escrita atomica tolerante a bloqueios curtos do Windows/OneDrive."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt >= 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _latest_micro_swing(
    rows: list[object],
    side: str,
    *,
    maximum_age: int | None = None,
) -> tuple[float | None, str]:
    field = "low" if side == "BUY" else "high"
    values = [_number(row, field) for row in rows]
    # Pivo 1+1 aceita microestrutura; ignora o candle-sinal no extremo direito.
    minimum_index = (
        max(1, len(values) - 1 - int(maximum_age))
        if maximum_age is not None
        else 1
    )
    for index in range(len(values) - 2, minimum_index - 1, -1):
        value = values[index]
        if value is None or values[index - 1] is None or values[index + 1] is None:
            continue
        confirmed = (
            value <= values[index - 1] and value <= values[index + 1]
            if side == "BUY"
            else value >= values[index - 1] and value >= values[index + 1]
        )
        if confirmed:
            return float(value), _time(rows[index])
    return None, "N/D"


def _latest_structural_swing(
    rows: list[object],
    side: str,
) -> tuple[float | None, str]:
    """Ultimo fundo/topo anterior confirmado por duas velas de cada lado."""
    field = "low" if side == "BUY" else "high"
    values = [_number(row, field) for row in rows]
    if any(value is None for value in values):
        return None, "N/D"
    parsed = [float(value) for value in values if value is not None]
    left = 2
    right = 2
    for index in range(len(parsed) - right - 1, left - 1, -1):
        value = parsed[index]
        neighbors_left = parsed[index - left : index]
        neighbors_right = parsed[index + 1 : index + 1 + right]
        confirmed = (
            all(value < item for item in neighbors_left)
            and all(value <= item for item in neighbors_right)
            if side == "BUY"
            else all(value > item for item in neighbors_left)
            and all(value >= item for item in neighbors_right)
        )
        if confirmed:
            return value, _time(rows[index])
    return None, "N/D"


def _structural_pivots(
    rows: list[object],
    side: str,
) -> list[tuple[int, float, str]]:
    """Lista pivôs 2+2 confirmados usando somente candles fechados."""
    normalized = str(side or "").upper()
    field = "low" if normalized == "BUY" else "high" if normalized == "SELL" else ""
    if not field:
        return []
    values = [_number(row, field) for row in rows]
    if any(value is None for value in values):
        return []
    parsed = [float(value) for value in values if value is not None]
    pivots: list[tuple[int, float, str]] = []
    for index in range(2, len(parsed) - 2):
        value = parsed[index]
        left = parsed[index - 2 : index]
        right = parsed[index + 1 : index + 3]
        confirmed = (
            all(value < item for item in left)
            and all(value <= item for item in right)
            if normalized == "BUY"
            else all(value > item for item in left)
            and all(value >= item for item in right)
        )
        if confirmed:
            pivots.append((index, value, _time(rows[index])))
    return pivots


def _model24_initial_fibonacci_target(
    rows: list[object],
    side: str,
    entry: float,
) -> tuple[float | None, str]:
    """Projeta 100% da última perna estrutural completa a partir da entrada.

    BUY mede do último fundo estrutural 2+2 até a máxima favorável concluída
    antes do candle-sinal. SELL mede do último topo 2+2 até a mínima favorável.
    O alvo é congelado no plano e nunca recorre à antiga distância fixa de
    7,5 pontos.
    """
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"} or float(entry or 0.0) <= 0.0:
        return None, "N/D"
    origin_pivots = _structural_pivots(rows, normalized)
    for origin_index, origin_price, _origin_time in reversed(origin_pivots):
        # O último M5 fechado é o candle-sinal da INITIAL. A perna anterior
        # termina antes dele para não incorporar o próprio gatilho ao alvo.
        candidates = rows[origin_index + 1 : -1]
        if not candidates:
            continue
        field = "high" if normalized == "BUY" else "low"
        priced = [
            (index, _number(row, field))
            for index, row in enumerate(candidates, start=origin_index + 1)
        ]
        priced = [(index, value) for index, value in priced if value is not None]
        if not priced:
            continue
        end_index, end_price_value = (
            max(priced, key=lambda item: float(item[1]))
            if normalized == "BUY"
            else min(priced, key=lambda item: float(item[1]))
        )
        end_price = float(end_price_value)
        leg = (
            end_price - origin_price
            if normalized == "BUY"
            else origin_price - end_price
        )
        if leg <= 0.0:
            continue
        target = (
            float(entry) + leg * MODEL_24_SETUP.initial_target_fibonacci_projection
            if normalized == "BUY"
            else float(entry) - leg * MODEL_24_SETUP.initial_target_fibonacci_projection
        )
        if target > 0.0:
            return round(float(target), 2), _time(rows[end_index])
    return None, "N/D"


def _model24_reentry_structural_target(
    rows: list[object],
    side: str,
    entry: float,
    *,
    maximum_age: int = 200,
) -> tuple[float | None, str]:
    """Retorna o fechamento do microtopo/microfundo confirmado 1+1."""
    if len(rows) < 3:
        return None, "N/D"
    normalized = str(side or "").upper()
    field = "high" if normalized == "BUY" else "low" if normalized == "SELL" else ""
    if not field:
        return None, "N/D"
    # O ultimo candle fechado define a pendente. O alvo pertence ao micro pivo
    # anterior mais recente, confirmado por uma vela de cada lado. A cotacao do
    # TP e o fechamento do candle que formou o microtopo/microfundo, nunca sua
    # maxima/minima.
    start = max(1, len(rows) - max(3, int(maximum_age)))
    for index in range(len(rows) - 2, start - 1, -1):
        extreme = _number(rows[index], field)
        target = _number(rows[index], "close")
        neighbors = [
            _number(rows[neighbor], field)
            for neighbor in (index - 1, index + 1)
        ]
        if extreme is None or target is None or any(value is None for value in neighbors):
            continue
        left = float(neighbors[0])
        right = float(neighbors[1])
        confirmed = (
            float(extreme) > left and float(extreme) >= right
            if normalized == "BUY"
            else float(extreme) < left and float(extreme) <= right
        )
        if not confirmed:
            continue
        valid = (
            float(target) > float(entry)
            if normalized == "BUY"
            else float(target) < float(entry)
        )
        if valid:
            return float(target), _time(rows[index])
        # O TP pertence ao micro pivo mais recente. Nao recue para uma
        # estrutura antiga apenas para obter um preco do lado lucrativo da
        # pendente; a reentrada deve aguardar novo encaixe estrutural.
        return None, "N/D"
    return None, "N/D"


def _model24_initial_cross_confirmation(
    values: list[float],
    *,
    require_rsi_cross: bool = MODEL_24_SETUP.initial_requires_rsi_cross,
) -> tuple[str, int | None, int | None, list[float]]:
    """Confirma cruzamentos mantidos, ainda que ocorram em M5 diferentes."""
    rsi_values = [
        _wilder_rsi(values[: index + 1], MODEL_24_SETUP.rsi_period)
        for index in range(len(values))
    ]
    if len(values) < MODEL_24_SETUP.sma_fast_period + 1:
        return "WAIT", None, None, rsi_values

    price_cross_up: int | None = None
    price_cross_down: int | None = None
    for index in range(MODEL_24_SETUP.sma_fast_period, len(values)):
        previous_sma = _sma(values[:index], MODEL_24_SETUP.sma_fast_period)
        current_sma = _sma(values[: index + 1], MODEL_24_SETUP.sma_fast_period)
        if values[index - 1] <= previous_sma and values[index] > current_sma:
            price_cross_up = index
        elif values[index - 1] >= previous_sma and values[index] < current_sma:
            price_cross_down = index

    rsi_cross_up: int | None = None
    rsi_cross_down: int | None = None
    for index in range(MODEL_24_SETUP.rsi_period + 1, len(values)):
        previous_rsi = rsi_values[index - 1]
        current_rsi = rsi_values[index]
        if previous_rsi <= MODEL_24_SETUP.rsi_level and current_rsi > MODEL_24_SETUP.rsi_level:
            rsi_cross_up = index
        elif previous_rsi >= MODEL_24_SETUP.rsi_level and current_rsi < MODEL_24_SETUP.rsi_level:
            rsi_cross_down = index

    sma20 = _sma(values, MODEL_24_SETUP.sma_fast_period)
    rsi14 = rsi_values[-1]
    if values[-1] > sma20 and rsi14 > MODEL_24_SETUP.rsi_level:
        if price_cross_up is not None and (
            not require_rsi_cross or rsi_cross_up is not None
        ):
            return "BUY", price_cross_up, rsi_cross_up, rsi_values
    elif values[-1] < sma20 and rsi14 < MODEL_24_SETUP.rsi_level:
        if price_cross_down is not None and (
            not require_rsi_cross or rsi_cross_down is not None
        ):
            return "SELL", price_cross_down, rsi_cross_down, rsi_values
    return "WAIT", None, None, rsi_values


def _sma(values: list[float], period: int) -> float:
    return sum(values[-period:]) / float(period)


def _wilder_rsi(values: list[float], period: int) -> float:
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / float(period)
    average_loss = sum(losses[:period]) / float(period)
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * (period - 1)) + gain) / float(period)
        average_loss = ((average_loss * (period - 1)) + loss) / float(period)
    if average_loss == 0.0:
        return 100.0 if average_gain > 0.0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _model24_atr(rows: list[object]) -> float:
    highs = [_number(row, "high") for row in rows]
    lows = [_number(row, "low") for row in rows]
    closes = [_number(row, "close") for row in rows]
    if (
        len(rows) <= MODEL_24_ATR_PERIOD
        or any(value is None for value in (*highs, *lows, *closes))
    ):
        return 0.0
    parsed_highs = [float(value) for value in highs if value is not None]
    parsed_lows = [float(value) for value in lows if value is not None]
    parsed_closes = [float(value) for value in closes if value is not None]
    true_ranges = [
        max(
            parsed_highs[index] - parsed_lows[index],
            abs(parsed_highs[index] - parsed_closes[index - 1]),
            abs(parsed_lows[index] - parsed_closes[index - 1]),
        )
        for index in range(1, len(parsed_closes))
    ]
    atr = sum(true_ranges[:MODEL_24_ATR_PERIOD]) / float(MODEL_24_ATR_PERIOD)
    for current in true_ranges[MODEL_24_ATR_PERIOD:]:
        atr = (
            (atr * (MODEL_24_ATR_PERIOD - 1)) + current
        ) / float(MODEL_24_ATR_PERIOD)
    return atr


def _model24_distance_atr(sma20: float, sma50: float, atr14: float) -> float:
    if atr14 <= 0.0:
        return 0.0
    return abs(float(sma20) - float(sma50)) / float(atr14)


def _number(row: object, field: str) -> float | None:
    if not field:
        return None
    aliases = {
        "open": ("open", "abertura"),
        "high": ("high", "maxima"),
        "low": ("low", "minima"),
        "close": ("close", "fechamento"),
    }
    candidates = aliases.get(field, (field,))
    value = None
    for candidate in candidates:
        value = (
            row.get(candidate)
            if isinstance(row, dict)
            else getattr(row, candidate, None)
        )
        if value is not None:
            break
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _time(row: object) -> str:
    if isinstance(row, dict):
        value = row.get("time", row.get("data"))
    else:
        value = None
        for field_name in ("time", "datetime", "timestamp", "data"):
            try:
                candidate = row[field_name]  # type: ignore[index]
            except (KeyError, IndexError, TypeError, ValueError):
                candidate = getattr(row, field_name, None)
            if candidate not in (None, "") and not isinstance(candidate, memoryview):
                value = candidate
                break
    if isinstance(value, datetime):
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        return normalized.isoformat()
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value or "N/D")


def _timestamp(value: object) -> float | None:
    if isinstance(value, datetime):
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        return normalized.timestamp()
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    text = str(value or "").strip()
    if not text or text == "N/D":
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None
