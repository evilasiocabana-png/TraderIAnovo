"""Modelo 3 ativo: XAUUSD/M5 com RSI14=50 e fechamento relativo a SMA20."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MODEL_3_ID = "MODELO_3_XAU_M5_RSI50_FLIP"
MODEL_3_SHORT_NAME = "M3"
MODEL_3_SYMBOL = "XAUUSD"
MODEL_3_TIMEFRAME = "M5"
MODEL_3_COMMENT = "TraderIA M3"
MODEL_3_ALPHA_ID = "ALPHAXAU3_RSI14_50_FLIP"
MODEL_3_ALPHA_VERSION = "M3_ENTRY_V2"
MODEL_3_BETA_ID = "BETAXAU3_RSI50_POSITION_FLIP"
MODEL_3_BETA_VERSION = "M3_EXIT_V1"
MODEL_3_BETA_MODE = "FULL_EXIT_AND_REVERSE_RSI50"
MODEL_3_STOP_MANAGEMENT = "M3_RSI50_POSITION_FLIP"
MODEL_3_ENTRY_ORDER_TYPE = "MARKET_ON_CLOSED_M5_RSI50_AND_SMA20"
MODEL_3_RSI_PERIOD = 14
MODEL_3_RSI_LEVEL = 50.0
MODEL_3_SMA_PERIOD = 20
MODEL_3_LOOKBACK_CANDLES = 52
MODEL_3_SWING_LEFT = 2
MODEL_3_SWING_RIGHT = 2
MODEL_3_STOP_BUFFER = 0.01


@dataclass(frozen=True)
class Model3EntryDecision:
    direction: str
    status: str
    reason: str
    current_candle_time: str = "N/D"
    closed_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    rsi14: float | None = None
    sma20: float | None = None
    closed_price: float | None = None
    last_swing_price: float | None = None
    last_swing_time: str = "N/D"

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
        )


@dataclass(frozen=True)
class Model3ExitDecision:
    action: str
    status: str
    reason: str
    closed_candle_time: str = "N/D"
    rsi14: float | None = None


def evaluate_model3_entry(
    candles: Iterable[object],
    *,
    stop_buffer: float = MODEL_3_STOP_BUFFER,
) -> Model3EntryDecision:
    """Combina RSI14/50 e fechamento relativo a SMA20 no ultimo M5 fechado."""
    rows = list(candles or ())
    minimum = MODEL_3_LOOKBACK_CANDLES
    if len(rows) < minimum:
        return Model3EntryDecision(
            direction="WAIT",
            status=f"M3_AQUECENDO_{len(rows)}_DE_{minimum}_CANDLES",
            reason=(
                f"M3 recebeu {len(rows)} de {minimum} candles M5 necessarios, "
                "incluindo o candle atual."
            ),
        )
    rows = rows[-MODEL_3_LOOKBACK_CANDLES:]

    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    if any(value is None for value in closes):
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_DADOS_INVALIDOS",
            reason="M3 recebeu candle M5 fechado sem preco valido.",
        )
    values = [float(value) for value in closes if value is not None]
    rsi14 = _wilder_rsi(values, MODEL_3_RSI_PERIOD)
    sma20 = sum(values[-MODEL_3_SMA_PERIOD:]) / float(MODEL_3_SMA_PERIOD)
    closed_price = values[-1]
    common = {
        "current_candle_time": _candle_time(rows[-1]),
        "closed_candle_time": _candle_time(closed_rows[-1]),
        "rsi14": rsi14,
        "sma20": sma20,
        "closed_price": closed_price,
    }
    if rsi14 > MODEL_3_RSI_LEVEL and closed_price > sma20:
        direction = "BUY"
    elif rsi14 < MODEL_3_RSI_LEVEL and closed_price < sma20:
        direction = "SELL"
    elif rsi14 == MODEL_3_RSI_LEVEL:
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_RSI50_NEUTRO",
            reason="RSI14 fechou exatamente em 50; manter estado e aguardar.",
            **common,
        )
    elif rsi14 > MODEL_3_RSI_LEVEL:
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_AGUARDA_FECHAMENTO_ACIMA_SMA20",
            reason=(
                f"RSI14={rsi14:.2f} esta acima de 50, mas o fechamento "
                f"{closed_price:.2f} ainda nao esta acima da SMA20 {sma20:.2f}."
            ),
            **common,
        )
    else:
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_AGUARDA_FECHAMENTO_ABAIXO_SMA20",
            reason=(
                f"RSI14={rsi14:.2f} esta abaixo de 50, mas o fechamento "
                f"{closed_price:.2f} ainda nao esta abaixo da SMA20 {sma20:.2f}."
            ),
            **common,
        )

    swing_price, swing_time = _last_confirmed_swing(closed_rows, direction)
    if swing_price is None:
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_SWING_NAO_CONFIRMADO",
            reason="M3 aguarda ultimo fundo/topo M5 confirmado para definir o SL.",
            **common,
        )

    entry = closed_price
    buffer = abs(float(stop_buffer))
    stop = swing_price - buffer if direction == "BUY" else swing_price + buffer
    valid = stop < entry if direction == "BUY" else stop > entry
    if not valid:
        return Model3EntryDecision(
            direction="WAIT",
            status="M3_STOP_INVALIDO",
            reason="O ultimo fundo/topo confirmado nao produz SL estrutural valido.",
            entry_price=entry,
            initial_stop=stop,
            last_swing_price=swing_price,
            last_swing_time=swing_time,
            **common,
        )

    return Model3EntryDecision(
        direction=direction,
        status=f"M3_{direction}_MERCADO_PRONTA",
        reason=(
            f"RSI14={rsi14:.2f} e fechamento={closed_price:.2f} "
            f"confirmado {'acima' if direction == 'BUY' else 'abaixo'} da "
            f"SMA20={sma20:.2f}: {direction} a mercado; "
            f"SL {buffer:g} alem do ultimo "
            f"{'fundo' if direction == 'BUY' else 'topo'} confirmado."
        ),
        entry_price=entry,
        initial_stop=stop,
        last_swing_price=swing_price,
        last_swing_time=swing_time,
        **common,
    )


def evaluate_model3_exit(candles: Iterable[object], side: str) -> Model3ExitDecision:
    """Fecha integralmente quando o RSI14 muda para o lado oposto de 50."""
    rows = list(candles or ())
    minimum = MODEL_3_RSI_PERIOD + 2
    if len(rows) < minimum:
        return Model3ExitDecision(
            action="HOLD_POSITION",
            status="M3_EXIT_CANDLES_INSUFICIENTES",
            reason=f"M3 exige ao menos {minimum} candles M5 para avaliar a saida.",
        )
    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    if any(value is None for value in closes):
        return Model3ExitDecision(
            action="HOLD_POSITION",
            status="M3_EXIT_DADOS_INVALIDOS",
            reason="M3 preservou a posicao porque faltou fechamento M5 valido.",
        )
    values = [float(value) for value in closes if value is not None]
    rsi14 = _wilder_rsi(values, MODEL_3_RSI_PERIOD)
    closed_time = _candle_time(closed_rows[-1])
    normalized_side = str(side or "").upper()
    if normalized_side == "BUY" and rsi14 < MODEL_3_RSI_LEVEL:
        return Model3ExitDecision(
            action="FULL_EXIT",
            status="M3_EXIT_BUY_RSI_ABAIXO_50",
            reason="RSI14 M5 fechou abaixo de 50; fechar BUY e liberar SELL.",
            closed_candle_time=closed_time,
            rsi14=rsi14,
        )
    if normalized_side == "SELL" and rsi14 > MODEL_3_RSI_LEVEL:
        return Model3ExitDecision(
            action="FULL_EXIT",
            status="M3_EXIT_SELL_RSI_ACIMA_50",
            reason="RSI14 M5 fechou acima de 50; fechar SELL e liberar BUY.",
            closed_candle_time=closed_time,
            rsi14=rsi14,
        )
    if normalized_side not in {"BUY", "SELL"}:
        return Model3ExitDecision(
            action="HOLD_POSITION",
            status="M3_EXIT_LADO_INVALIDO",
            reason="M3 recebeu lado de posicao invalido; nenhuma acao executada.",
            closed_candle_time=closed_time,
            rsi14=rsi14,
        )
    return Model3ExitDecision(
        action="HOLD_POSITION",
        status=f"M3_HOLD_{normalized_side}",
        reason="RSI14 M5 permanece no mesmo lado de 50 da posicao.",
        closed_candle_time=closed_time,
        rsi14=rsi14,
    )


def model3_parameters() -> dict[str, object]:
    return {
        "symbol": MODEL_3_SYMBOL,
        "timeframe": MODEL_3_TIMEFRAME,
        "rsi_period": MODEL_3_RSI_PERIOD,
        "rsi_level": MODEL_3_RSI_LEVEL,
        "sma_period": MODEL_3_SMA_PERIOD,
        "lookback_candles": MODEL_3_LOOKBACK_CANDLES,
        "buy_rule": "CLOSED_RSI14>50_AND_CLOSE>SMA20",
        "sell_rule": "CLOSED_RSI14<50_AND_CLOSE<SMA20",
        "neutral_rule": "CLOSED_RSI14==50_HOLD_OR_WAIT",
        "entry_order_type": MODEL_3_ENTRY_ORDER_TYPE,
        "swing_left": MODEL_3_SWING_LEFT,
        "swing_right": MODEL_3_SWING_RIGHT,
        "stop_buffer": MODEL_3_STOP_BUFFER,
        "take_profit_enabled": False,
        "full_exit_enabled": True,
        "buy_full_exit": "CLOSED_RSI14<50",
        "sell_full_exit": "CLOSED_RSI14>50",
        "reverse_after_full_exit": True,
        "signal_requires_closed_m5_confirmation": True,
    }


def _last_confirmed_swing(
    rows: list[object], direction: str
) -> tuple[float | None, str]:
    field = "low" if direction == "BUY" else "high"
    values = [_candle_value(row, field) for row in rows]
    if any(value is None for value in values):
        return None, "N/D"
    parsed = [float(value) for value in values if value is not None]
    left = MODEL_3_SWING_LEFT
    right = MODEL_3_SWING_RIGHT
    for index in range(len(parsed) - right - 1, left - 1, -1):
        value = parsed[index]
        neighbors_left = parsed[index - left : index]
        neighbors_right = parsed[index + 1 : index + 1 + right]
        if field == "low":
            confirmed = all(value < item for item in neighbors_left) and all(
                value <= item for item in neighbors_right
            )
        else:
            confirmed = all(value > item for item in neighbors_left) and all(
                value >= item for item in neighbors_right
            )
        if confirmed:
            return value, _candle_time(rows[index])
    return None, "N/D"


def _wilder_rsi(values: list[float], period: int) -> float:
    if len(values) <= period:
        return 50.0
    changes = [current - previous for previous, current in zip(values, values[1:])]
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


def _candle_value(candle: object, field: str) -> float | None:
    aliases = {
        "open": ("open", "abertura"),
        "high": ("high", "maxima"),
        "low": ("low", "minima"),
        "close": ("close", "fechamento"),
    }
    for name in aliases.get(field, (field,)):
        if isinstance(candle, dict):
            value: Any = candle.get(name)
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
