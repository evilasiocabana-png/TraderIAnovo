"""Modelo 26: confluencia Smart Money deterministica em XAUUSD/M1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import hashlib


MODEL_26_ID = "MODELO_26_XAU_M5_SMART_MONEY"
MODEL_26_ALPHA_ID = "ALPHA026_SMART_MONEY_CONFLUENCE"
MODEL_26_ALPHA_VERSION = "M26_ENTRY_V1"
MODEL_26_BETA_ID = "BETA026_STRUCTURAL_LIQUIDITY_EXIT"
MODEL_26_BETA_VERSION = "M26_EXIT_V1"
MODEL_26_SOURCE = "MODEL_26_SMART_MONEY_RULE"
MODEL_26_STOP_MANAGEMENT = "FIXED_STOP"
MODEL_26_SYMBOL = "XAUUSD"
MODEL_26_TIMEFRAME = "M1"
MODEL_26_VOLUME = 0.01
MODEL_26_CLOSED_CANDLES = 200
MODEL_26_RAW_CANDLES = MODEL_26_CLOSED_CANDLES + 1
MODEL_26_PIVOT_LEFT = 2
MODEL_26_PIVOT_RIGHT = 2
MODEL_26_ATR_PERIOD = 14
MODEL_26_DISPLACEMENT_ATR_MIN = 0.60
MODEL_26_BODY_SHARE_MIN = 0.60
MODEL_26_FVG_ATR_MIN = 0.10
MODEL_26_ORDER_BLOCK_LOOKBACK = 5
MODEL_26_ENTRY_EXPIRY_CANDLES = 12
MODEL_26_MIN_RISK_REWARD = 2.0
MODEL_26_PIP_SIZE = 0.01
MODEL_26_CONTRACT_VERSION = "M26_SMART_MONEY_V3_20260825"
MODEL_26_CONTRACT_FINGERPRINT = hashlib.sha256(
    "|".join(
        (
            MODEL_26_CONTRACT_VERSION,
            MODEL_26_SYMBOL,
            MODEL_26_TIMEFRAME,
            "STRUCTURE_2_2",
            "LIQUIDITY_SWEEP_CLOSE_BACK",
            "BOS_DISPLACEMENT_0.60_ATR",
            "FVG_3_CANDLES_0.10_ATR",
            "ORDER_BLOCK_LAST_OPPOSITE_5",
            "RETEST_EXPIRY_12",
            "MIN_RR_2",
            "VOLUME_0.01",
        )
    ).encode("utf-8")
).hexdigest()[:16]


@dataclass(frozen=True)
class _Bar:
    time: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Model26Decision:
    direction: str = "WAIT"
    status: str = "M26_AGUARDA_DADOS"
    reason: str = "M26 aguarda snapshot XAUUSD/M1."
    current_candle_time: str = "N/D"
    closed_candle_time: str = "N/D"
    market_structure: str = "UNDEFINED"
    structure_ok: bool = False
    liquidity_sweep_ok: bool = False
    bos_displacement_ok: bool = False
    fvg_ok: bool = False
    order_block_ok: bool = False
    retest_ok: bool = False
    entry_price: float | None = None
    initial_stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    atr14: float | None = None
    sweep_level: float | None = None
    bos_level: float | None = None
    fvg_low: float | None = None
    fvg_high: float | None = None
    order_block_low: float | None = None
    order_block_high: float | None = None
    poi_low: float | None = None
    poi_high: float | None = None
    setup_id: str = ""

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
            and self.target is not None
            and self.risk_reward >= MODEL_26_MIN_RISK_REWARD
            and all(
                (
                    self.structure_ok,
                    self.liquidity_sweep_ok,
                    self.bos_displacement_ok,
                    self.fvg_ok,
                    self.order_block_ok,
                    self.retest_ok,
                )
            )
        )


def model26_parameters() -> dict[str, object]:
    return {
        "symbol": MODEL_26_SYMBOL,
        "timeframe": MODEL_26_TIMEFRAME,
        "closed_candles": MODEL_26_CLOSED_CANDLES,
        "pivot_left": MODEL_26_PIVOT_LEFT,
        "pivot_right": MODEL_26_PIVOT_RIGHT,
        "displacement_atr_min": MODEL_26_DISPLACEMENT_ATR_MIN,
        "body_share_min": MODEL_26_BODY_SHARE_MIN,
        "fvg_atr_min": MODEL_26_FVG_ATR_MIN,
        "order_block_lookback": MODEL_26_ORDER_BLOCK_LOOKBACK,
        "entry_expiry_candles": MODEL_26_ENTRY_EXPIRY_CANDLES,
        "minimum_risk_reward": MODEL_26_MIN_RISK_REWARD,
        "volume": MODEL_26_VOLUME,
        "active_entry_order_type": "MARKET",
        "contract_version": MODEL_26_CONTRACT_VERSION,
        "contract_fingerprint": MODEL_26_CONTRACT_FINGERPRINT,
    }


def is_model26(value: object) -> bool:
    return str(value or "").strip().upper().startswith(MODEL_26_ID)


def evaluate_model26_entry(candles: Iterable[object]) -> Model26Decision:
    """Avalia somente candles fechados; o ultimo item e a vela em formacao."""
    raw = list(candles or ())[-MODEL_26_RAW_CANDLES:]
    current_time = _time(raw[-1]) if raw else "N/D"
    if len(raw) < MODEL_26_RAW_CANDLES:
        return Model26Decision(
            status=f"M26_AQUECENDO_{max(0, len(raw) - 1)}_DE_{MODEL_26_CLOSED_CANDLES}",
            reason=(
                f"M26 recebeu {max(0, len(raw) - 1)} de "
                f"{MODEL_26_CLOSED_CANDLES} candles M1 fechados."
            ),
            current_candle_time=current_time,
        )
    try:
        bars = [_bar(row) for row in raw[:-1]]
    except (TypeError, ValueError):
        return Model26Decision(
            status="M26_DADOS_INVALIDOS",
            reason="M26 recebeu candle M1 sem OHLC valido.",
            current_candle_time=current_time,
        )
    atr = _atr(bars, MODEL_26_ATR_PERIOD)
    common = {
        "current_candle_time": current_time,
        "closed_candle_time": bars[-1].time,
        "atr14": atr,
    }
    if atr <= 0:
        return Model26Decision(
            status="M26_ATR_INVALIDO",
            reason="M26 nao calculou ATR14 positivo nas velas fechadas.",
            **common,
        )
    pivots_high, pivots_low = _pivots(bars)
    structure = _current_structure(pivots_high, pivots_low)
    structure_ok = structure != "UNDEFINED"
    latest_progress: Model26Decision | None = None
    start = max(5, len(bars) - 50)
    for sweep_index in range(start, len(bars) - 1):
        prior_highs = [item for item in pivots_high if item[0] < sweep_index]
        prior_lows = [item for item in pivots_low if item[0] < sweep_index]
        if len(prior_highs) < 2 or len(prior_lows) < 2:
            continue
        local_structure = _structure(prior_highs[-2:], prior_lows[-2:])
        if local_structure == "UNDEFINED":
            continue
        direction = "BUY" if local_structure == "BULLISH" else "SELL"
        swing_index, sweep_level = (
            prior_lows[-1] if direction == "BUY" else prior_highs[-1]
        )
        sweep = bars[sweep_index]
        swept = (
            sweep.low < sweep_level and sweep.close > sweep_level
            if direction == "BUY"
            else sweep.high > sweep_level and sweep.close < sweep_level
        )
        if not swept:
            continue
        progress_common = dict(
            **common,
            market_structure=local_structure,
            structure_ok=True,
            liquidity_sweep_ok=True,
            sweep_level=sweep_level,
        )
        latest_progress = Model26Decision(
            status="M26_AGUARDA_BOS_DESLOCAMENTO",
            reason="Varredura confirmada; aguarda BOS com deslocamento.",
            **progress_common,
        )
        bos_level = prior_highs[-1][1] if direction == "BUY" else prior_lows[-1][1]
        for displacement_index in range(
            sweep_index + 1, min(sweep_index + 4, len(bars))
        ):
            displacement = bars[displacement_index]
            body = abs(displacement.close - displacement.open)
            candle_range = max(displacement.high - displacement.low, 1e-12)
            bos = (
                displacement.close > bos_level and displacement.close > displacement.open
                if direction == "BUY"
                else displacement.close < bos_level and displacement.close < displacement.open
            )
            impulse = (
                body >= MODEL_26_DISPLACEMENT_ATR_MIN * atr
                and body / candle_range >= MODEL_26_BODY_SHARE_MIN
            )
            if not (bos and impulse) or displacement_index < 2:
                continue
            fvg = _fvg(bars, displacement_index, direction, atr)
            if fvg is None:
                latest_progress = Model26Decision(
                    status="M26_AGUARDA_FVG",
                    reason="BOS e deslocamento confirmados; FVG minimo ainda ausente.",
                    bos_displacement_ok=True,
                    bos_level=bos_level,
                    **progress_common,
                )
                continue
            order_block = _order_block(bars, displacement_index, direction)
            if order_block is None:
                latest_progress = Model26Decision(
                    status="M26_AGUARDA_ORDER_BLOCK",
                    reason="FVG confirmado; ultima vela contraria do impulso nao encontrada.",
                    bos_displacement_ok=True,
                    fvg_ok=True,
                    bos_level=bos_level,
                    fvg_low=fvg[0],
                    fvg_high=fvg[1],
                    **progress_common,
                )
                continue
            poi_low, poi_high = _poi(fvg, order_block)
            age = len(bars) - 1 - displacement_index
            setup_id = f"M26|{direction}|{sweep.time}|{displacement.time}"
            stage = dict(
                bos_displacement_ok=True,
                fvg_ok=True,
                order_block_ok=True,
                bos_level=bos_level,
                fvg_low=fvg[0],
                fvg_high=fvg[1],
                order_block_low=order_block[0],
                order_block_high=order_block[1],
                poi_low=poi_low,
                poi_high=poi_high,
                setup_id=setup_id,
                **progress_common,
            )
            if age > MODEL_26_ENTRY_EXPIRY_CANDLES:
                latest_progress = Model26Decision(
                    status="M26_SETUP_EXPIRADO",
                    reason="Confluencia expirou sem reteste em ate 12 candles M5.",
                    **stage,
                )
                continue
            retest = bars[-1]
            touched = retest.low <= poi_high and retest.high >= poi_low
            midpoint = (poi_low + poi_high) / 2.0
            confirmed = (
                touched and retest.close > retest.open and retest.close >= midpoint
                if direction == "BUY"
                else touched and retest.close < retest.open and retest.close <= midpoint
            )
            if not confirmed:
                latest_progress = Model26Decision(
                    status="M26_AGUARDA_RETESTE_FVG_ORDER_BLOCK",
                    reason="Confluencia valida; aguarda reteste confirmado da zona FVG/OB.",
                    **stage,
                )
                continue
            entry = retest.close
            stop = (
                min(sweep.low, order_block[0]) - MODEL_26_PIP_SIZE
                if direction == "BUY"
                else max(sweep.high, order_block[1]) + MODEL_26_PIP_SIZE
            )
            risk = abs(entry - stop)
            if risk <= 0 or (direction == "BUY" and stop >= entry) or (
                direction == "SELL" and stop <= entry
            ):
                continue
            minimum_target = (
                entry + MODEL_26_MIN_RISK_REWARD * risk
                if direction == "BUY"
                else entry - MODEL_26_MIN_RISK_REWARD * risk
            )
            external_liquidity = bos_level
            target = (
                max(minimum_target, external_liquidity)
                if direction == "BUY"
                else min(minimum_target, external_liquidity)
            )
            rr = abs(target - entry) / risk
            return Model26Decision(
                direction=direction,
                status="M26_PLANO_VALIDO",
                reason=(
                    f"{direction}: estrutura, varredura, BOS/deslocamento, FVG, "
                    "order block e reteste confirmados em candle M5 fechado."
                ),
                retest_ok=True,
                entry_price=entry,
                initial_stop=stop,
                target=target,
                risk_reward=rr,
                **stage,
            )
    if latest_progress is not None:
        return latest_progress
    return Model26Decision(
        status=("M26_AGUARDA_VARREDURA_LIQUIDEZ" if structure_ok else "M26_AGUARDA_ESTRUTURA_2_2"),
        reason=(
            "Estrutura confirmada; aguarda varredura de liquidez com fechamento de volta."
            if structure_ok
            else "Aguarda dois topos e dois fundos confirmados 2+2 para definir a estrutura."
        ),
        market_structure=structure,
        structure_ok=structure_ok,
        **common,
    )


def _bar(row: object) -> _Bar:
    return _Bar(
        time=_time(row),
        open=float(_value(row, "abertura", "open")),
        high=float(_value(row, "maxima", "high")),
        low=float(_value(row, "minima", "low")),
        close=float(_value(row, "fechamento", "close")),
    )


def _value(row: object, *names: str) -> object:
    for name in names:
        if isinstance(row, dict) and name in row:
            return row[name]
        if hasattr(row, name):
            return getattr(row, name)
    raise ValueError(f"Campo ausente: {names[0]}")


def _time(row: object) -> str:
    for name in ("data", "time", "timestamp"):
        if isinstance(row, dict) and row.get(name) is not None:
            return str(row[name])
        if hasattr(row, name):
            return str(getattr(row, name))
    return "N/D"


def _atr(bars: list[_Bar], period: int) -> float:
    ranges: list[float] = []
    for index in range(1, len(bars)):
        row, previous = bars[index], bars[index - 1]
        ranges.append(max(row.high - row.low, abs(row.high - previous.close), abs(row.low - previous.close)))
    sample = ranges[-period:]
    return sum(sample) / len(sample) if sample else 0.0


def _pivots(bars: list[_Bar]) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    left, right = MODEL_26_PIVOT_LEFT, MODEL_26_PIVOT_RIGHT
    for index in range(left, len(bars) - right):
        window = bars[index - left : index + right + 1]
        if bars[index].high == max(row.high for row in window):
            highs.append((index, bars[index].high))
        if bars[index].low == min(row.low for row in window):
            lows.append((index, bars[index].low))
    return highs, lows


def _structure(highs: list[tuple[int, float]], lows: list[tuple[int, float]]) -> str:
    if len(highs) < 2 or len(lows) < 2:
        return "UNDEFINED"
    if highs[-1][1] > highs[-2][1] and lows[-1][1] > lows[-2][1]:
        return "BULLISH"
    if highs[-1][1] < highs[-2][1] and lows[-1][1] < lows[-2][1]:
        return "BEARISH"
    return "UNDEFINED"


def _current_structure(highs: list[tuple[int, float]], lows: list[tuple[int, float]]) -> str:
    return _structure(highs[-2:], lows[-2:])


def _fvg(
    bars: list[_Bar],
    index: int,
    direction: str,
    atr: float,
) -> tuple[float, float] | None:
    first, third = bars[index - 2], bars[index]
    if (
        direction == "BUY"
        and third.low > first.high
        and third.low - first.high >= MODEL_26_FVG_ATR_MIN * atr
    ):
        return first.high, third.low
    if (
        direction == "SELL"
        and third.high < first.low
        and first.low - third.high >= MODEL_26_FVG_ATR_MIN * atr
    ):
        return third.high, first.low
    return None


def _order_block(
    bars: list[_Bar],
    index: int,
    direction: str,
) -> tuple[float, float] | None:
    start = max(0, index - MODEL_26_ORDER_BLOCK_LOOKBACK)
    for row in reversed(bars[start:index]):
        opposite = (
            row.close < row.open if direction == "BUY" else row.close > row.open
        )
        if opposite:
            return row.low, row.high
    return None


def _poi(
    fvg: tuple[float, float],
    order_block: tuple[float, float],
) -> tuple[float, float]:
    overlap_low = max(fvg[0], order_block[0])
    overlap_high = min(fvg[1], order_block[1])
    return (overlap_low, overlap_high) if overlap_low <= overlap_high else fvg
