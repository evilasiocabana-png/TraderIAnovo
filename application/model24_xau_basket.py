"""Modelo 24: cesta XAU/M5 com entradas RSI50 e alvo financeiro global."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
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
    source = model24_source_model_id(model24_variant_id(source_model))
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
    source = model24_source_model_id(model24_variant_id(source_model))
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        sources = dict(payload.get("sources") or {})
        sources[source] = {
            "trend_side": side,
            "initial_consumed": True,
            "last_entry_candle": str(candle_time or "N/D"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        payload = {"sources": sources}
        MODEL_24_RUNTIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = MODEL_24_RUNTIME_STATE_PATH.with_suffix(f".{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(MODEL_24_RUNTIME_STATE_PATH)


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
    """Avalia a entrada inicial por micro-pivo ou a reentrada simples no RSI50."""
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
    normalized_role = str(entry_role or "INITIAL").upper()
    buy_structure_ok = (
        values[-1] > sma20 if normalized_role == "INITIAL" else sma20 > sma50
    )
    sell_structure_ok = (
        values[-1] < sma20 if normalized_role == "INITIAL" else sma20 < sma50
    )
    if previous_rsi14 < 50.0 < rsi14 and buy_structure_ok:
        side = "BUY"
    elif previous_rsi14 > 50.0 > rsi14 and sell_structure_ok:
        side = "SELL"
    else:
        return Model24EntryDecision(
            status="M24_AGUARDA_CRUZAMENTO_RSI50_COM_SMA",
            reason=(
                "Aguardar RSI14 cruzar 50 e confirmar a estrutura exigida para "
                "a etapa no fechamento M5."
            ),
            **common,
        )
    entry = float(values[-1])
    if normalized_role == "INITIAL":
        swing, swing_time = _latest_micro_swing(closed, side, maximum_age=5)
        if swing is None:
            return Model24EntryDecision(
                direction="WAIT",
                status="M24_INITIAL_AGUARDA_MICRO_PIVO_CONFIRMADO",
                reason=(
                    "O cruzamento RSI50 ocorreu, mas a entrada inicial exige "
                    "microfundo/microtopo 1+1 confirmado nos ultimos cinco M5."
                ),
                entry_price=entry,
                **common,
            )
    else:
        # A segunda reentrada usa exatamente o extremo do candle anterior.
        swing = _number(closed[-2], "low" if side == "BUY" else "high")
        swing_time = _time(closed[-2])
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
        status=f"M24_{normalized_role}_{side}_RSI50_MERCADO_PRONTA",
        reason=(
            f"{side} {normalized_role} a mercado no cruzamento confirmado do RSI14 "
            "em 50, alinhado a SMA20/50; SL estrutural definido pelo contrato."
        ),
        entry_price=entry,
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
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(f".{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
        temporary.replace(self.state_path)


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
    value = row.get(field) if isinstance(row, dict) else getattr(row, field, None)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _time(row: object) -> str:
    value = row.get("time") if isinstance(row, dict) else getattr(row, "time", None)
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value or "N/D")
