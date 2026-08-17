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


MODEL_24_ID = "MODELO_24_XAU_RSI50_BASKET"
MODEL_24_ALPHA_ID = "ALPHA024_XAU_RSI50_MULTI_SOURCE"
MODEL_24_ALPHA_VERSION = "M24_ENTRY_V1"
MODEL_24_BETA_ID = "BETA024_BASKET_FULL_EXIT_1000"
MODEL_24_BETA_VERSION = "M24_EXIT_V1"
MODEL_24_ENTRY_SOURCE = "MODEL_24_XAU_SOURCE_SIGNAL"
MODEL_24_EXIT_POLICY = "M24_SOURCE_EXIT_PLUS_BASKET_1000"
MODEL_24_FULL_EXIT_USD = 1000.0
MODEL_24_TIMEFRAME = "M5"
MODEL_24_SYMBOL = "XAUUSD"
MODEL_24_STATE_PATH = Path(".traderia") / "model24_basket_state.json"
MODEL_24_RUNTIME_STATE_PATH = Path(".traderia") / "model24_runtime_state.json"
MODEL_24_AUDIT_PATH = Path(".traderia") / "model24_basket_audit.jsonl"
MODEL_24_SOURCE_MODEL_NUMBERS = (8, 10, 18, 19, 20, 21, 22)
MODEL_24_SOURCE_MODEL_IDS = (
    "MODELO_8_XAU_M5_SMA_RSI_REENTRY",
    "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
    "MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75",
    "MODELO_19_XAU_M5_SMA_RSI_ADX_REENTRY_TP75",
    "MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75",
    "MODELO_21_XAU_M5_SMA_RSI_SMA50_SLOPE_REENTRY_TP75",
    "MODELO_22_XAU_M5_SMA_RSI_TREND_FILTERS_REENTRY_TP75",
)

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
    number = operational_model_number(source_operational_model)
    if number not in MODEL_24_SOURCE_MODEL_NUMBERS:
        raise ValueError("M24 aceita somente as fontes M8, M10 e M18-M22.")
    return f"{MODEL_24_ID}_SOURCE_M{number}"


def model24_source_model_id(value: object) -> str:
    match = re.search(r"_SOURCE_M(\d{1,2})(?:_|\b|$)", str(value or "").upper())
    return f"M{int(match.group(1))}" if match is not None else "N/D"


def model24_order_comment(value: object) -> str:
    source = model24_source_model_id(value)
    return "TraderIA M24" if source == "N/D" else f"TraderIA M24 S{source[1:]}"


def model24_position_matches(position: object) -> bool:
    return bool(re.search(r"\bM24\b", str(getattr(position, "comment", "") or "").upper()))


def model24_position_net(position: object) -> float:
    return sum(
        float(getattr(position, field, 0.0) or 0.0)
        for field in ("profit", "swap", "commission", "fee")
    )


def model24_market_entry_role(source_model: object, trend_side: object) -> str:
    """Primeiro RSI50 da tendencia e inicial; os seguintes sao reentradas."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        state = dict(dict(payload.get("sources") or {}).get(source) or {})
    if str(state.get("trend_side") or "").upper() != side:
        return "INITIAL"
    return "REENTRY" if bool(state.get("initial_consumed")) else "INITIAL"


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
            ):
                state.pop(field_name, None)
        state.update({
            "trend_side": side,
            "initial_consumed": True,
            "last_entry_candle": str(candle_time or "N/D"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        sources[source] = state
        _write_runtime_state({"sources": sources})


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
    """Arma o descarte da primeira reentrada apos Full Exit RSI 70/30."""
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
                    "skip_first_reentry_after_extreme": True,
                    "blocked_reentry_opportunity_key": "",
                    "last_extreme_exit_event_key": event_key,
                    "last_extreme_exit_status": str(exit_status or "").upper(),
                    "last_extreme_exit_candle": str(candle_time or "N/D"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            sources[source] = state
            _write_runtime_state({"sources": sources})


def evaluate_model24_reentry_opportunity(
    source_model: object,
    trend_side: object,
    opportunity_key: object,
) -> Model24ReentryGateDecision:
    """Ignora a primeira oportunidade unica e libera a segunda apos RSI 70/30."""
    source = _model24_source_key(source_model)
    side = str(trend_side or "").upper()
    key = str(opportunity_key or "").strip()
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        state = dict(sources.get(source) or {})
        if not bool(state.get("skip_first_reentry_after_extreme")):
            return Model24ReentryGateDecision(
                allowed=True,
                status="M24_REENTRY_SEGUNDA_OPORTUNIDADE_LIBERADA",
                reason="Nao existe descarte de primeira reentrada pendente.",
            )
        if str(state.get("trend_side") or "").upper() != side:
            return Model24ReentryGateDecision(
                allowed=True,
                status="M24_REENTRY_NOVA_DIRECAO_LIBERADA",
                reason="A trava do Full Exit pertence a outra direcao.",
            )
        if not key:
            return Model24ReentryGateDecision(
                allowed=False,
                status="M24_REENTRY_AGUARDA_IDENTIFICAR_OPORTUNIDADE",
                reason="A reentrada aguarda uma vela M5 fechada identificavel.",
            )
        blocked_key = str(state.get("blocked_reentry_opportunity_key") or "")
        if not blocked_key:
            state.update(
                {
                    "blocked_reentry_opportunity_key": key,
                    "blocked_reentry_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            sources[source] = state
            _write_runtime_state({"sources": sources})
            blocked_key = key
        if blocked_key == key:
            return Model24ReentryGateDecision(
                allowed=False,
                status="M24_REENTRY_PRIMEIRA_OPORTUNIDADE_IGNORADA",
                reason=(
                    "Primeira oportunidade de reentrada apos Full Exit RSI 70/30 "
                    "ignorada; aguardar a segunda oportunidade em nova vela M5."
                ),
                blocked_opportunity_key=blocked_key,
            )
        state.update(
            {
                "skip_first_reentry_after_extreme": False,
                "released_reentry_opportunity_key": key,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        sources[source] = state
        _write_runtime_state({"sources": sources})
        return Model24ReentryGateDecision(
            allowed=True,
            status="M24_REENTRY_SEGUNDA_OPORTUNIDADE_LIBERADA",
            reason="Segunda oportunidade valida apos Full Exit RSI 70/30 liberada.",
            blocked_opportunity_key=blocked_key,
        )


def _model24_source_key(value: object) -> str:
    if is_model24(value):
        source = model24_source_model_id(value)
        if source != "N/D":
            return source
    number = operational_model_number(value)
    if number not in MODEL_24_SOURCE_MODEL_NUMBERS:
        raise ValueError("M24 aceita somente as fontes M8, M10 e M18-M22.")
    return f"M{number}"


def _write_runtime_state(payload: dict[str, Any]) -> None:
    _atomic_json_write(MODEL_24_RUNTIME_STATE_PATH, payload)


def _load_runtime_state() -> dict[str, Any]:
    try:
        payload = json.loads(MODEL_24_RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class Model24EntryDecision:
    direction: str = "WAIT"
    status: str = "M24_AGUARDA_RSI50"
    reason: str = "Aguardando cruzamento confirmado do RSI14 no nivel 50."
    closed_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    rsi14: float | None = None
    previous_rsi14: float | None = None
    micro_swing_price: float | None = None
    micro_swing_time: str = "N/D"
    price_cross_time: str = "N/D"
    rsi_cross_time: str = "N/D"

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
        )


def evaluate_model24_rsi50_market_entry(
    candles: Iterable[object],
    *,
    entry_role: str = "INITIAL",
) -> Model24EntryDecision:
    """Avalia a entrada inicial; RSI e preco podem confirmar em velas distintas."""
    rows = list(candles or ())[-201:]
    normalized_role = str(entry_role or "INITIAL").upper()
    if normalized_role == "REENTRY":
        return evaluate_model24_pending_reentry(rows)
    if len(rows) < 201:
        return Model24EntryDecision(
            status=f"M24_AQUECENDO_{len(rows)}_DE_201_CANDLES",
            reason="M24 exige 200 candles M5 fechados e o candle atual em formacao.",
        )
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if any(value is None for value in closes):
        return Model24EntryDecision(
            status="M24_DADOS_INVALIDOS",
            reason="Candle M5 fechado sem preco de fechamento valido.",
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, 20)
    sma50 = _sma(values, 50)
    cross_side, price_cross_index, rsi_cross_index, rsi_values = (
        _model24_initial_cross_confirmation(values)
    )
    rsi14 = rsi_values[-1]
    previous_rsi14 = rsi_values[-2]
    common = {
        "closed_candle_time": _time(closed[-1]),
        "sma20": sma20,
        "sma50": sma50,
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
    if cross_side not in {"BUY", "SELL"}:
        return Model24EntryDecision(
            status="M24_INITIAL_AGUARDA_CRUZAMENTOS_PRECO_SMA20_E_RSI50",
            reason=(
                "Entrada inicial aguarda os cruzamentos confirmados do preco "
                "na SMA20 e do RSI14 no nivel 50 na mesma direcao; os eventos "
                "podem ocorrer em velas M5 diferentes."
            ),
            **common,
        )
    side = cross_side
    entry = float(values[-1])
    swing, swing_time = _latest_micro_swing(closed, side, maximum_age=5)
    if swing is None:
        return Model24EntryDecision(
            direction="WAIT",
            status="M24_INITIAL_AGUARDA_MICRO_PIVO_CONFIRMADO",
            reason=(
                "A entrada inicial exige microfundo/microtopo 1+1 confirmado "
                "nos ultimos cinco M5."
            ),
            entry_price=entry,
            **common,
        )
    stop = float(swing or 0.0)
    valid = stop < entry if side == "BUY" else stop > entry
    if not valid:
        return Model24EntryDecision(
            direction="WAIT",
            status="M24_STOP_MICRO_ESTRUTURAL_INVALIDO",
            reason="O microtopo/microfundo mais recente nao produz SL valido.",
            entry_price=entry,
            initial_stop=stop,
            micro_swing_price=stop,
            micro_swing_time=swing_time,
            **common,
        )
    return Model24EntryDecision(
        direction=side,
        status=f"M24_INITIAL_{side}_CRUZAMENTOS_SMA20_RSI50_MERCADO_PRONTA",
        reason=(
            f"{side} inicial a mercado: preco e RSI14 cruzaram seus niveis na "
            "mesma direcao, ainda que em velas distintas; SL no micro pivo."
        ),
        entry_price=entry,
        initial_stop=stop,
        micro_swing_price=stop,
        micro_swing_time=swing_time,
        **common,
    )


def evaluate_model24_pending_reentry(
    candles: Iterable[object],
) -> Model24EntryDecision:
    """Reentrada pendente pelo lado atual da SMA20 e do RSI50, sem novo cruzamento."""
    rows = list(candles or ())[-201:]
    if len(rows) < 201:
        return Model24EntryDecision(
            status=f"M24_AQUECENDO_{len(rows)}_DE_201_CANDLES",
            reason="M24 exige 200 candles M5 fechados e o candle atual em formacao.",
        )
    closed = rows[:-1]
    closes = [_number(row, "close") for row in closed]
    if any(value is None for value in closes):
        return Model24EntryDecision(
            status="M24_DADOS_INVALIDOS",
            reason="Candle M5 fechado sem preco de fechamento valido.",
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, 20)
    sma50 = _sma(values, 50)
    rsi14 = _wilder_rsi(values, 14)
    previous_rsi14 = _wilder_rsi(values[:-1], 14)
    common = {
        "closed_candle_time": _time(closed[-1]),
        "sma20": sma20,
        "sma50": sma50,
        "rsi14": rsi14,
        "previous_rsi14": previous_rsi14,
    }
    if values[-1] > sma20 and rsi14 > 50.0:
        side = "BUY"
        entry = _number(closed[-1], "high")
        order_type = "BUY_STOP"
    elif values[-1] < sma20 and rsi14 < 50.0:
        side = "SELL"
        entry = _number(closed[-1], "low")
        order_type = "SELL_STOP"
    else:
        return Model24EntryDecision(
            status="M24_REENTRY_AGUARDA_PRECO_SMA20_E_RSI50_ALINHADOS",
            reason=(
                "Reentrada aguarda fechamento e RSI14 no mesmo lado da "
                "SMA20/linha 50; nao exige novo cruzamento."
            ),
            **common,
        )
    swing, swing_time = _latest_micro_swing(closed, side, maximum_age=5)
    if swing is None:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_AGUARDA_MICRO_PIVO_CONFIRMADO",
            reason="Reentrada pendente exige micro pivo 1+1 recente para o SL.",
            **common,
        )
    trigger = float(entry or 0.0)
    stop = float(swing)
    valid = stop < trigger if side == "BUY" else stop > trigger
    if not valid:
        return Model24EntryDecision(
            direction=side,
            status="M24_REENTRY_STOP_MICRO_PIVO_INVALIDO",
            reason="Micro pivo recente nao produz SL valido para a ordem pendente.",
            entry_price=trigger,
            initial_stop=stop,
            micro_swing_price=stop,
            micro_swing_time=swing_time,
            **common,
        )
    return Model24EntryDecision(
        direction=side,
        status=f"M24_REENTRY_{side}_{order_type}_SMA20_PRONTA",
        reason=(
            f"Reentrada {order_type}: fechamento e RSI14 permanecem do lado "
            "permitido, sem novo cruzamento; gatilho no extremo do ultimo M5."
        ),
        entry_price=trigger,
        initial_stop=stop,
        micro_swing_price=stop,
        micro_swing_time=swing_time,
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


def _model24_initial_cross_confirmation(
    values: list[float],
) -> tuple[str, int | None, int | None, list[float]]:
    """Confirma os ultimos cruzamentos SMA20/RSI50, mesmo em velas distintas."""
    rsi_values = [
        _wilder_rsi(values[: index + 1], 14)
        for index in range(len(values))
    ]
    if len(values) < 21:
        return "WAIT", None, None, rsi_values

    price_cross_up: int | None = None
    price_cross_down: int | None = None
    for index in range(20, len(values)):
        previous_sma = _sma(values[:index], 20)
        current_sma = _sma(values[: index + 1], 20)
        if values[index - 1] <= previous_sma and values[index] > current_sma:
            price_cross_up = index
        elif values[index - 1] >= previous_sma and values[index] < current_sma:
            price_cross_down = index

    rsi_cross_up: int | None = None
    rsi_cross_down: int | None = None
    for index in range(15, len(values)):
        previous_rsi = rsi_values[index - 1]
        current_rsi = rsi_values[index]
        if previous_rsi <= 50.0 and current_rsi > 50.0:
            rsi_cross_up = index
        elif previous_rsi >= 50.0 and current_rsi < 50.0:
            rsi_cross_down = index

    sma20 = _sma(values, 20)
    rsi14 = rsi_values[-1]
    if values[-1] > sma20 and rsi14 > 50.0:
        if price_cross_up is not None and rsi_cross_up is not None:
            return "BUY", price_cross_up, rsi_cross_up, rsi_values
    elif values[-1] < sma20 and rsi14 < 50.0:
        if price_cross_down is not None and rsi_cross_down is not None:
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
    value = (
        row.get("time", row.get("data"))
        if isinstance(row, dict)
        else getattr(row, "time", getattr(row, "data", None))
    )
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value or "N/D")
