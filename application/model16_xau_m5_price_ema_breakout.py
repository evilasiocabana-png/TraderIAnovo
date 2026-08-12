"""Modelo 16: ouro M5 por preco/EMA20 e rompimento do candle anterior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MODEL_16_ID = "MODELO_16_XAU_M5_PRICE_EMA20_BREAKOUT_TRAILING"
MODEL_16_SHORT_NAME = "M16"
MODEL_16_SYMBOL = "XAUUSD"
MODEL_16_TIMEFRAME = "M5"
MODEL_16_COMMENT = "TraderIA M16"
MODEL_16_ALPHA_ID = "ALPHAXAU16_PRICE_EMA20_BREAKOUT"
MODEL_16_ALPHA_VERSION = "M16_ENTRY_V1"
MODEL_16_BETA_ID = "BETAXAU16_PREVIOUS_CANDLE_TRAILING"
MODEL_16_BETA_VERSION = "M16_EXIT_V1"
MODEL_16_STOP_MANAGEMENT = "M16_PREVIOUS_CANDLE_TRAILING_STOP"
MODEL_16_PIP_SIZE = 0.01
MODEL_16_EMA_PERIOD = 20


@dataclass(frozen=True)
class Model16EntryDecision:
    """Resultado puro da leitura do preco atual contra a EMA20."""

    direction: str
    status: str
    reason: str
    current_candle_time: str = "N/D"
    previous_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    current_price: float | None = None
    ema20: float | None = None
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


def evaluate_model16_entry(
    candles: Iterable[object],
    *,
    pip_size: float = MODEL_16_PIP_SIZE,
) -> Model16EntryDecision:
    """Prepara STOP no extremo anterior conforme preco acima/abaixo da EMA20."""
    rows = list(candles or ())
    minimum = MODEL_16_EMA_PERIOD + 1
    if len(rows) < minimum:
        return Model16EntryDecision(
            direction="WAIT",
            status="M16_CANDLES_INSUFICIENTES",
            reason=f"M16 exige ao menos {minimum} candles M5, incluindo o atual.",
        )

    current = rows[-1]
    previous = rows[-2]
    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    current_price = _candle_value(current, "close")
    if any(value is None for value in closes) or current_price is None:
        return Model16EntryDecision(
            direction="WAIT",
            status="M16_DADOS_INVALIDOS",
            reason="M16 recebeu candle M5 sem fechamento valido.",
        )

    previous_high = _candle_value(previous, "high")
    previous_low = _candle_value(previous, "low")
    current_high = _candle_value(current, "high")
    current_low = _candle_value(current, "low")
    current_time = _candle_time(current)
    previous_time = _candle_time(previous)
    if None in {previous_high, previous_low, current_high, current_low}:
        return Model16EntryDecision(
            direction="WAIT",
            status="M16_DADOS_INVALIDOS",
            reason="M16 recebeu candle M5 sem maxima ou minima valida.",
            current_candle_time=current_time,
            previous_candle_time=previous_time,
        )

    ema20 = _ema([float(value) for value in closes if value is not None], MODEL_16_EMA_PERIOD)
    buffer = abs(float(pip_size))
    buy_entry = float(previous_high) + buffer
    sell_entry = float(previous_low) - buffer
    buy_stop = float(previous_low)
    sell_stop = float(previous_high)
    common = {
        "current_candle_time": current_time,
        "previous_candle_time": previous_time,
        "current_price": float(current_price),
        "ema20": ema20,
        "previous_high": float(previous_high),
        "previous_low": float(previous_low),
        "current_high": float(current_high),
        "current_low": float(current_low),
    }

    if float(current_price) > ema20:
        if float(current_high) >= buy_entry:
            return Model16EntryDecision(
                direction="WAIT",
                status="M16_BUY_STOP_PERDIDA",
                reason=(
                    "Preco acima da EMA20, mas o candle atual ja rompeu o "
                    "gatilho; M16 nao persegue o preco a mercado."
                ),
                entry_price=buy_entry,
                initial_stop=buy_stop,
                **common,
            )
        return Model16EntryDecision(
            direction="BUY",
            status="M16_BUY_STOP_PRONTA",
            reason=(
                "Preco acima da EMA20; preparar BUY STOP 1 pip acima da "
                "maxima anterior."
            ),
            entry_price=buy_entry,
            initial_stop=buy_stop,
            **common,
        )

    if float(current_price) < ema20:
        if float(current_low) <= sell_entry:
            return Model16EntryDecision(
                direction="WAIT",
                status="M16_SELL_STOP_PERDIDA",
                reason=(
                    "Preco abaixo da EMA20, mas o candle atual ja rompeu o "
                    "gatilho; M16 nao persegue o preco a mercado."
                ),
                entry_price=sell_entry,
                initial_stop=sell_stop,
                **common,
            )
        return Model16EntryDecision(
            direction="SELL",
            status="M16_SELL_STOP_PRONTA",
            reason=(
                "Preco abaixo da EMA20; preparar SELL STOP 1 pip abaixo da "
                "minima anterior."
            ),
            entry_price=sell_entry,
            initial_stop=sell_stop,
            **common,
        )

    return Model16EntryDecision(
        direction="WAIT",
        status="M16_PRECO_NA_EMA20",
        reason="Preco sem distancia direcional da EMA20.",
        **common,
    )


def model16_stop_management_parameters() -> dict[str, object]:
    """Parametros congelados usados pelo Position Manager do M16."""
    return {
        "timeframe": MODEL_16_TIMEFRAME,
        "ema_period": MODEL_16_EMA_PERIOD,
        "pip_size": MODEL_16_PIP_SIZE,
        "entry_buffer_pips": 1,
        "stop_buffer_pips": 0,
        "entry_order_type": "STOP_PENDING",
        "pending_expiration": "CURRENT_M5_CANDLE_END",
        "take_profit_enabled": False,
        "early_exit_enabled": False,
        "full_exit_enabled": False,
    }


def model16_previous_candle_stop(
    candles: Iterable[object],
    side: str,
) -> tuple[float | None, str]:
    """Calcula o SL no extremo exato do ultimo candle fechado."""
    rows = list(candles or ())
    if len(rows) < 2:
        return None, "N/D"
    previous = rows[-2]
    normalized_side = str(side or "").upper()
    field = "low" if normalized_side == "BUY" else "high"
    if normalized_side not in {"BUY", "SELL"}:
        return None, _candle_time(previous)
    value = _candle_value(previous, field)
    return (float(value) if value is not None else None, _candle_time(previous))


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
