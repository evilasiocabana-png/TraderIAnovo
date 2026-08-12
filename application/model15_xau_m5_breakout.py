"""Modelo 15: breakout M5 do ouro com trailing pelo candle anterior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MODEL_15_ID = "MODELO_15_XAU_M5_EMA_BREAKOUT_TRAILING"
MODEL_15_SHORT_NAME = "M15"
MODEL_15_SYMBOL = "XAUUSD"
MODEL_15_TIMEFRAME = "M5"
MODEL_15_COMMENT = "TraderIA M15"
MODEL_15_ALPHA_ID = "ALPHAXAU15_EMA_BREAKOUT"
MODEL_15_ALPHA_VERSION = "M15_ENTRY_V1"
MODEL_15_BETA_ID = "BETAXAU15_PREVIOUS_CANDLE_TRAILING"
MODEL_15_BETA_VERSION = "M15_EXIT_V1"
MODEL_15_STOP_MANAGEMENT = "PREVIOUS_CANDLE_TRAILING_STOP"
MODEL_15_PIP_SIZE = 0.01
MODEL_15_EMA_FAST = 20
MODEL_15_EMA_SLOW = 50


@dataclass(frozen=True)
class Model15EntryDecision:
    """Resultado puro da leitura do candle atual contra o anterior fechado."""

    direction: str
    status: str
    reason: str
    current_candle_time: str = "N/D"
    previous_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    previous_high: float | None = None
    previous_low: float | None = None
    current_high: float | None = None
    current_low: float | None = None

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
        )


def evaluate_model15_entry(
    candles: Iterable[object],
    *,
    pip_size: float = MODEL_15_PIP_SIZE,
) -> Model15EntryDecision:
    """Prepara a ordem STOP antes do rompimento do extremo anterior."""
    rows = list(candles or ())
    minimum = MODEL_15_EMA_SLOW + 1
    if len(rows) < minimum:
        return Model15EntryDecision(
            direction="WAIT",
            status="M15_CANDLES_INSUFICIENTES",
            reason=f"M15 exige ao menos {minimum} candles M5, incluindo o atual.",
        )

    current = rows[-1]
    previous = rows[-2]
    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    if any(value is None for value in closes):
        return Model15EntryDecision(
            direction="WAIT",
            status="M15_DADOS_INVALIDOS",
            reason="M15 recebeu candle M5 sem fechamento valido.",
        )

    previous_high = _candle_value(previous, "high")
    previous_low = _candle_value(previous, "low")
    current_high = _candle_value(current, "high")
    current_low = _candle_value(current, "low")
    current_time = _candle_time(current)
    previous_time = _candle_time(previous)
    if None in {previous_high, previous_low, current_high, current_low}:
        return Model15EntryDecision(
            direction="WAIT",
            status="M15_DADOS_INVALIDOS",
            reason="M15 recebeu candle M5 sem maxima ou minima valida.",
            current_candle_time=current_time,
            previous_candle_time=previous_time,
        )

    ema20 = _ema([float(value) for value in closes if value is not None], MODEL_15_EMA_FAST)
    ema50 = _ema([float(value) for value in closes if value is not None], MODEL_15_EMA_SLOW)
    buffer = abs(float(pip_size))
    buy_entry = float(previous_high) + buffer
    sell_entry = float(previous_low) - buffer
    buy_stop = float(previous_low)
    sell_stop = float(previous_high)

    common = {
        "current_candle_time": current_time,
        "previous_candle_time": previous_time,
        "ema20": ema20,
        "ema50": ema50,
        "previous_high": float(previous_high),
        "previous_low": float(previous_low),
        "current_high": float(current_high),
        "current_low": float(current_low),
    }
    if ema20 > ema50:
        if float(current_high) >= buy_entry:
            return Model15EntryDecision(
                direction="WAIT",
                status="M15_BUY_STOP_PERDIDA",
                reason=(
                    "EMA20 acima da EMA50, mas o candle atual ja rompeu o "
                    "gatilho; M15 nao persegue o preco a mercado."
                ),
                entry_price=buy_entry,
                initial_stop=buy_stop,
                **common,
            )
        return Model15EntryDecision(
            direction="BUY",
            status="M15_BUY_STOP_PRONTA",
            reason=(
                "EMA20 acima da EMA50; preparar BUY STOP 1 pip acima da "
                "maxima anterior."
            ),
            entry_price=buy_entry,
            initial_stop=buy_stop,
            **common,
        )
    if ema20 < ema50:
        if float(current_low) <= sell_entry:
            return Model15EntryDecision(
                direction="WAIT",
                status="M15_SELL_STOP_PERDIDA",
                reason=(
                    "EMA20 abaixo da EMA50, mas o candle atual ja rompeu o "
                    "gatilho; M15 nao persegue o preco a mercado."
                ),
                entry_price=sell_entry,
                initial_stop=sell_stop,
                **common,
            )
        return Model15EntryDecision(
            direction="SELL",
            status="M15_SELL_STOP_PRONTA",
            reason=(
                "EMA20 abaixo da EMA50; preparar SELL STOP 1 pip abaixo da "
                "minima anterior."
            ),
            entry_price=sell_entry,
            initial_stop=sell_stop,
            **common,
        )
    return Model15EntryDecision(
        direction="WAIT",
        status="M15_EMAS_NEUTRAS",
        reason="EMA20 e EMA50 sem direcao definida.",
        **common,
    )


def model15_stop_management_parameters() -> dict[str, object]:
    """Parametros congelados usados pelo Position Manager do M15."""
    return {
        "timeframe": MODEL_15_TIMEFRAME,
        "ema_fast": MODEL_15_EMA_FAST,
        "ema_slow": MODEL_15_EMA_SLOW,
        "pip_size": MODEL_15_PIP_SIZE,
        "entry_buffer_pips": 1,
        "stop_buffer_pips": 0,
        "entry_order_type": "STOP_PENDING",
        "pending_expiration": "CURRENT_M5_CANDLE_END",
        "take_profit_enabled": False,
        "early_exit_enabled": False,
        "full_exit_enabled": False,
    }


def model15_previous_candle_stop(
    candles: Iterable[object],
    side: str,
    *,
    pip_size: float = MODEL_15_PIP_SIZE,
) -> tuple[float | None, str]:
    """Calcula o SL no extremo exato do ultimo candle fechado."""
    rows = list(candles or ())
    if len(rows) < 2:
        return None, "N/D"
    previous = rows[-2]
    normalized_side = str(side or "").upper()
    if normalized_side == "BUY":
        low = _candle_value(previous, "low")
        return (
            float(low) if low is not None else None,
            _candle_time(previous),
        )
    if normalized_side == "SELL":
        high = _candle_value(previous, "high")
        return (
            float(high) if high is not None else None,
            _candle_time(previous),
        )
    return None, _candle_time(previous)


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    factor = 2.0 / (float(period) + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = (float(value) * factor) + (result * (1.0 - factor))
    return result


def _candle_value(candle: object, field: str) -> float | None:
    aliases = {
        "open": ("open", "abertura"),
        "high": ("high", "maxima"),
        "low": ("low", "minima"),
        "close": ("close", "fechamento"),
    }
    for name in aliases.get(field, (field,)):
        value: Any
        if isinstance(candle, dict):
            value = candle.get(name)
        else:
            value = getattr(candle, name, None)
            if value is None:
                try:
                    value = candle[name]  # type: ignore[index]
                except (KeyError, IndexError, TypeError, ValueError):
                    value = None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0.0:
            return parsed
    return None


def _candle_time(candle: object) -> str:
    for name in ("data", "time", "datetime", "timestamp"):
        if isinstance(candle, dict):
            value = candle.get(name)
        else:
            value = getattr(candle, name, None)
            if value is None:
                try:
                    value = candle[name]  # type: ignore[index]
                except (KeyError, IndexError, TypeError, ValueError):
                    value = None
        if value not in (None, ""):
            return str(value)
    return "N/D"
