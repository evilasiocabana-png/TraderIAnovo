"""Modelos B-E do XAUUSD/M5 derivados do setup SMA20/50 + RSI50."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from application.model8_xau_m5_sma_rsi_reentry import (
    MODEL_8_SYMBOL,
    MODEL_8_TIMEFRAME,
    Model8EntryDecision,
    _candle_value,
    _sma,
    evaluate_model8_entry,
    evaluate_model8_native_entry,
)
from application.operational_indicator_window import OPERATIONAL_INDICATOR_RAW_CANDLES
from application.mt5_native_m5_indicators import MT5NativeM5IndicatorSnapshot


MODEL_9_ID = "MODELO_9_XAU_M5_SMA_RSI_ADX"
MODEL_10_ID = "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR"
MODEL_11_ID = "MODELO_11_XAU_M5_SMA_RSI_SMA50_SLOPE"
MODEL_12_ID = "MODELO_12_XAU_M5_SMA_RSI_TREND_FILTERS"
MODEL_18_ID = "MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75"
MODEL_19_ID = "MODELO_19_XAU_M5_SMA_RSI_ADX_REENTRY_TP75"
MODEL_20_ID = "MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75"
MODEL_21_ID = "MODELO_21_XAU_M5_SMA_RSI_SMA50_SLOPE_REENTRY_TP75"
MODEL_22_ID = "MODELO_22_XAU_M5_SMA_RSI_TREND_FILTERS_REENTRY_TP75"
XAU_BASE_TREND_FILTER_MODEL_IDS = (
    MODEL_10_ID,
)
XAU_RETIRED_BASE_TREND_FILTER_MODEL_IDS = (
    MODEL_9_ID,
    MODEL_11_ID,
    MODEL_12_ID,
)
XAU_IMPROVED_REENTRY_MODEL_IDS = (
    MODEL_18_ID,
    MODEL_19_ID,
    MODEL_20_ID,
    MODEL_21_ID,
    MODEL_22_ID,
)
XAU_TREND_FILTER_MODEL_IDS = XAU_BASE_TREND_FILTER_MODEL_IDS
XAU_ALL_TREND_FILTER_MODEL_IDS = (
    *XAU_TREND_FILTER_MODEL_IDS,
    *XAU_IMPROVED_REENTRY_MODEL_IDS,
)
XAU_POSITION_MANAGEMENT_MODEL_IDS = (
    *XAU_RETIRED_BASE_TREND_FILTER_MODEL_IDS,
    *XAU_ALL_TREND_FILTER_MODEL_IDS,
)
XAU_REENTRY_TARGET_MODE = "LAST_CONFIRMED_M5_SWING_BEFORE_PULLBACK"
XAU_MAX_REENTRIES_PER_SIGNAL = None
MODEL_ADX_PERIOD = 14
MODEL_ATR_PERIOD = 14
MODEL_9_ADX_MIN = 25.0
MODEL_10_DISTANCE_ATR_MIN = 0.25
MODEL_11_SLOPE_LOOKBACK = 1
MODEL_11_SLOPE_ATR_MIN = 0.05


@dataclass(frozen=True)
class XAUTrendFilterSpec:
    model_id: str
    number: int
    setup: str
    alpha_id: str
    alpha_version: str
    beta_id: str
    beta_version: str
    stop_management: str
    source: str
    source_model_id: str
    reentry_target_points: float = 0.0
    reentry_structural_target: bool = False
    max_reentries_per_signal: int | None = None
    requires_adx: bool = False
    requires_distance_atr: bool = False
    requires_sma50_slope: bool = False

    @property
    def short_name(self) -> str:
        return f"M{self.number}"

    @property
    def comment(self) -> str:
        return f"TraderIA M{self.number}"


MODEL_SPECS = {
    MODEL_9_ID: XAUTrendFilterSpec(
        model_id=MODEL_9_ID,
        number=9,
        setup="B",
        alpha_id="ALPHAXAU9_SMA_RSI_ADX",
        alpha_version="M9_ENTRY_V2",
        beta_id="BETAXAU9_RSI70_30_SMA_FULL_EXIT",
        beta_version="M9_EXIT_V2",
        stop_management="M9_SMA_RSI_FULL_EXIT",
        source="MODEL_9_MANUAL_RULE",
        source_model_id=MODEL_9_ID,
        requires_adx=True,
    ),
    MODEL_10_ID: XAUTrendFilterSpec(
        model_id=MODEL_10_ID,
        number=10,
        setup="C",
        alpha_id="ALPHAXAU10_SMA_RSI_DISTANCE_ATR",
        alpha_version="M10_ENTRY_V2",
        beta_id="BETAXAU10_RSI70_30_SMA_FULL_EXIT",
        beta_version="M10_EXIT_V2",
        stop_management="M10_SMA_RSI_FULL_EXIT",
        source="MODEL_10_MANUAL_RULE",
        source_model_id=MODEL_10_ID,
        requires_distance_atr=True,
    ),
    MODEL_11_ID: XAUTrendFilterSpec(
        model_id=MODEL_11_ID,
        number=11,
        setup="D",
        alpha_id="ALPHAXAU11_SMA_RSI_SMA50_SLOPE",
        alpha_version="M11_ENTRY_V2",
        beta_id="BETAXAU11_RSI70_30_SMA_FULL_EXIT",
        beta_version="M11_EXIT_V2",
        stop_management="M11_SMA_RSI_FULL_EXIT",
        source="MODEL_11_MANUAL_RULE",
        source_model_id=MODEL_11_ID,
        requires_sma50_slope=True,
    ),
    MODEL_12_ID: XAUTrendFilterSpec(
        model_id=MODEL_12_ID,
        number=12,
        setup="E",
        alpha_id="ALPHAXAU12_SMA_RSI_TREND_FILTERS",
        alpha_version="M12_ENTRY_V2",
        beta_id="BETAXAU12_RSI70_30_SMA_FULL_EXIT",
        beta_version="M12_EXIT_V2",
        stop_management="M12_SMA_RSI_FULL_EXIT",
        source="MODEL_12_MANUAL_RULE",
        source_model_id=MODEL_12_ID,
        requires_adx=True,
        requires_distance_atr=True,
        requires_sma50_slope=True,
    ),
    MODEL_18_ID: XAUTrendFilterSpec(
        model_id=MODEL_18_ID,
        number=18,
        setup="A+",
        alpha_id="ALPHAXAU18_M8_REENTRY_STRUCTURAL_TARGET",
        alpha_version="M18_ENTRY_V2",
        beta_id="BETAXAU18_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        beta_version="M18_EXIT_V2",
        stop_management="M18_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        source="MODEL_18_FROM_M8_REENTRY_STRUCTURAL_TARGET",
        source_model_id="MODELO_8_XAU_M5_SMA_RSI_REENTRY",
        reentry_structural_target=True,
        max_reentries_per_signal=XAU_MAX_REENTRIES_PER_SIGNAL,
    ),
    MODEL_19_ID: XAUTrendFilterSpec(
        model_id=MODEL_19_ID,
        number=19,
        setup="B+",
        alpha_id="ALPHAXAU19_M9_REENTRY_STRUCTURAL_TARGET",
        alpha_version="M19_ENTRY_V2",
        beta_id="BETAXAU19_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        beta_version="M19_EXIT_V2",
        stop_management="M19_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        source="MODEL_19_FROM_M9_REENTRY_STRUCTURAL_TARGET",
        source_model_id=MODEL_9_ID,
        reentry_structural_target=True,
        max_reentries_per_signal=XAU_MAX_REENTRIES_PER_SIGNAL,
        requires_adx=True,
    ),
    MODEL_20_ID: XAUTrendFilterSpec(
        model_id=MODEL_20_ID,
        number=20,
        setup="C+",
        alpha_id="ALPHAXAU20_M10_REENTRY_STRUCTURAL_TARGET",
        alpha_version="M20_ENTRY_V2",
        beta_id="BETAXAU20_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        beta_version="M20_EXIT_V2",
        stop_management="M20_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        source="MODEL_20_FROM_M10_REENTRY_STRUCTURAL_TARGET",
        source_model_id=MODEL_10_ID,
        reentry_structural_target=True,
        max_reentries_per_signal=XAU_MAX_REENTRIES_PER_SIGNAL,
        requires_distance_atr=True,
    ),
    MODEL_21_ID: XAUTrendFilterSpec(
        model_id=MODEL_21_ID,
        number=21,
        setup="D+",
        alpha_id="ALPHAXAU21_M11_REENTRY_STRUCTURAL_TARGET",
        alpha_version="M21_ENTRY_V2",
        beta_id="BETAXAU21_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        beta_version="M21_EXIT_V2",
        stop_management="M21_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        source="MODEL_21_FROM_M11_REENTRY_STRUCTURAL_TARGET",
        source_model_id=MODEL_11_ID,
        reentry_structural_target=True,
        max_reentries_per_signal=XAU_MAX_REENTRIES_PER_SIGNAL,
        requires_sma50_slope=True,
    ),
    MODEL_22_ID: XAUTrendFilterSpec(
        model_id=MODEL_22_ID,
        number=22,
        setup="E+",
        alpha_id="ALPHAXAU22_M12_REENTRY_STRUCTURAL_TARGET",
        alpha_version="M22_ENTRY_V2",
        beta_id="BETAXAU22_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        beta_version="M22_EXIT_V2",
        stop_management="M22_STRUCTURAL_TARGET_RSI50_FULL_EXIT",
        source="MODEL_22_FROM_M12_REENTRY_STRUCTURAL_TARGET",
        source_model_id=MODEL_12_ID,
        reentry_structural_target=True,
        max_reentries_per_signal=XAU_MAX_REENTRIES_PER_SIGNAL,
        requires_adx=True,
        requires_distance_atr=True,
        requires_sma50_slope=True,
    ),
}


@dataclass(frozen=True)
class XAUTrendFilterDecision:
    model_id: str
    setup: str
    base: Model8EntryDecision
    filter_allowed: bool
    status: str
    reason: str
    adx14: float | None = None
    atr14: float | None = None
    distance_atr: float | None = None
    sma50_slope: float | None = None
    sma50_slope_atr: float | None = None
    passed_filters: tuple[str, ...] = ()
    failed_filters: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.base.ready and self.filter_allowed


def trend_filter_spec(model_id: object) -> XAUTrendFilterSpec | None:
    return MODEL_SPECS.get(str(model_id or "").upper())


def evaluate_xau_trend_filter_entry(
    model_id: str,
    candles: Iterable[object],
    *,
    awaiting_reentry_side: str | None = None,
) -> XAUTrendFilterDecision:
    """Aplica somente o filtro incremental B-E sobre o gatilho puro do M8."""
    spec = trend_filter_spec(model_id)
    if spec is None:
        raise ValueError(f"Modelo de filtro XAU desconhecido: {model_id}")
    rows = list(candles or ())
    required_rows = OPERATIONAL_INDICATOR_RAW_CANDLES
    if len(rows) < required_rows:
        status = (
            f"M{spec.number}_AQUECENDO_{len(rows)}_DE_{required_rows}_CANDLES"
        )
        base = evaluate_model8_entry(rows)
        return XAUTrendFilterDecision(
            model_id=spec.model_id,
            setup=spec.setup,
            base=replace(base, status=status),
            filter_allowed=False,
            status=status,
            reason=(
                f"M{spec.number} aquecendo dados: recebeu {len(rows)} de "
                f"{required_rows} candles M5 necessarios."
            ),
            failed_filters=("CANDLE_WARMUP",),
        )
    base = evaluate_model8_entry(
        rows,
        awaiting_reentry_side=awaiting_reentry_side,
    )
    closed_rows = rows[:-1]
    highs = _series(closed_rows, "high")
    lows = _series(closed_rows, "low")
    closes = _series(closed_rows, "close")
    if spec.requires_sma50_slope and len(closes) < 50 + MODEL_11_SLOPE_LOOKBACK:
        status = f"M{spec.number}_CANDLES_INSUFICIENTES_SMA50_SLOPE"
        return XAUTrendFilterDecision(
            model_id=spec.model_id,
            setup=spec.setup,
            base=replace(base, direction="WAIT", status=status),
            filter_allowed=False,
            status=status,
            reason=(
                f"M{spec.number} exige ao menos "
                f"{50 + MODEL_11_SLOPE_LOOKBACK} candles M5 fechados para a inclinacao."
            ),
            failed_filters=("SMA50_SLOPE_HISTORY",),
        )
    atr14 = _wilder_atr(highs, lows, closes, MODEL_ATR_PERIOD)
    adx14 = _wilder_adx(highs, lows, closes, MODEL_ADX_PERIOD)
    distance_atr = (
        abs(float(base.sma20 or 0.0) - float(base.sma50 or 0.0)) / atr14
        if atr14 > 0.0
        else 0.0
    )
    current_sma50 = _sma(closes, 50)
    earlier_sma50 = _sma(closes[:-MODEL_11_SLOPE_LOOKBACK], 50)
    sma50_slope = current_sma50 - earlier_sma50
    trend_direction = (
        base.direction
        if base.direction in {"BUY", "SELL"}
        else "BUY"
        if float(base.sma20 or 0.0) > float(base.sma50 or 0.0)
        else "SELL"
    )
    directional_slope = sma50_slope if trend_direction == "BUY" else -sma50_slope
    sma50_slope_atr = directional_slope / atr14 if atr14 > 0.0 else 0.0

    passed: list[str] = []
    failed: list[str] = []
    if spec.requires_adx:
        (passed if adx14 > MODEL_9_ADX_MIN else failed).append(
            f"ADX14>{MODEL_9_ADX_MIN:g}"
        )
    if spec.requires_distance_atr:
        (passed if distance_atr >= MODEL_10_DISTANCE_ATR_MIN else failed).append(
            f"DISTANCE_ATR>={MODEL_10_DISTANCE_ATR_MIN:g}"
        )
    if spec.requires_sma50_slope:
        (passed if sma50_slope_atr >= MODEL_11_SLOPE_ATR_MIN else failed).append(
            f"SMA50_SLOPE_ATR>={MODEL_11_SLOPE_ATR_MIN:g}"
        )
    allowed = not failed
    filter_code = _filter_code(spec)
    if not allowed:
        status = f"M{spec.number}_{filter_code}_BLOQUEADO"
        reason = (
            f"Setup {spec.setup}: {base.reason} Filtro bloqueado: "
            + ", ".join(failed)
            + "."
        )
    elif base.ready:
        order_label = (
            base.entry_order_type
            if base.entry_order_type in {"BUY_STOP", "SELL_STOP"}
            else "MERCADO"
        )
        status = f"M{spec.number}_{filter_code}_OK_{base.direction}_{order_label}_PRONTA"
        reason = f"Setup {spec.setup} liberado: " + ", ".join(passed) + "."
    else:
        base_status = str(base.status).removeprefix("M8_")
        status = f"M{spec.number}_{filter_code}_OK_{base_status}"
        reason = (
            f"Setup {spec.setup}: filtros atuais aprovados ({', '.join(passed)}); "
            f"{base.reason}"
        )
    return XAUTrendFilterDecision(
        model_id=spec.model_id,
        setup=spec.setup,
        base=replace(base, status=status, reason=reason),
        filter_allowed=allowed,
        status=status,
        reason=reason,
        adx14=adx14,
        atr14=atr14,
        distance_atr=distance_atr,
        sma50_slope=sma50_slope,
        sma50_slope_atr=sma50_slope_atr,
        passed_filters=tuple(passed),
        failed_filters=tuple(failed),
    )


def evaluate_xau_native_trend_filter_entry(
    model_id: str,
    snapshot: MT5NativeM5IndicatorSnapshot,
    *,
    awaiting_reentry_side: str | None = None,
) -> XAUTrendFilterDecision:
    """Aplica B-E sobre indicadores e pivos ja calculados pelo MT5."""
    spec = trend_filter_spec(model_id)
    if spec is None:
        raise ValueError(f"Modelo de filtro XAU desconhecido: {model_id}")
    base = evaluate_model8_native_entry(
        snapshot,
        awaiting_reentry_side=awaiting_reentry_side,
    )
    direction = (
        base.direction
        if base.direction in {"BUY", "SELL"}
        else "BUY" if snapshot.sma20 > snapshot.sma50 else "SELL"
    )
    slope_atr = (
        snapshot.sma50_slope_atr
        if direction == "BUY"
        else -snapshot.sma50_slope_atr
    )
    passed: list[str] = []
    failed: list[str] = []
    if spec.requires_adx:
        (passed if snapshot.adx14 > MODEL_9_ADX_MIN else failed).append("ADX14>25")
    if spec.requires_distance_atr:
        (passed if snapshot.distance_atr >= MODEL_10_DISTANCE_ATR_MIN else failed).append(
            "DISTANCE_ATR>=0.25"
        )
    if spec.requires_sma50_slope:
        (passed if slope_atr >= MODEL_11_SLOPE_ATR_MIN else failed).append(
            "SMA50_SLOPE_ATR>=0.05"
        )
    filter_code = _filter_code(spec)
    allowed = not failed
    if failed:
        status = f"M{spec.number}_{filter_code}_BLOQUEADO"
        reason = f"MT5 nativo, Setup {spec.setup} bloqueado: {', '.join(failed)}."
    elif base.ready:
        order_label = (
            base.entry_order_type
            if base.entry_order_type in {"BUY_STOP", "SELL_STOP"}
            else "MERCADO"
        )
        status = f"M{spec.number}_{filter_code}_OK_{base.direction}_{order_label}_PRONTA"
        reason = f"MT5 nativo, Setup {spec.setup} liberado: {', '.join(passed) or 'BASE'}."
    else:
        status = f"M{spec.number}_{filter_code}_OK_{base.status.removeprefix('M8_')}"
        reason = f"MT5 nativo, filtros aprovados. {base.reason}"
    return XAUTrendFilterDecision(
        model_id=spec.model_id,
        setup=spec.setup,
        base=replace(base, status=status, reason=reason),
        filter_allowed=allowed,
        status=status,
        reason=reason,
        adx14=snapshot.adx14,
        atr14=snapshot.atr14,
        distance_atr=snapshot.distance_atr,
        sma50_slope=snapshot.sma50 - snapshot.previous_sma50,
        sma50_slope_atr=slope_atr,
        passed_filters=tuple(passed),
        failed_filters=tuple(failed),
    )


def xau_trend_filter_parameters(model_id: str) -> dict[str, object]:
    spec = trend_filter_spec(model_id)
    if spec is None:
        raise ValueError(f"Modelo de filtro XAU desconhecido: {model_id}")
    return {
        "setup": spec.setup,
        "symbol": MODEL_8_SYMBOL,
        "timeframe": MODEL_8_TIMEFRAME,
        "sma_fast": 20,
        "sma_slow": 50,
        "rsi_period": 14,
        "rsi_level": 50.0,
        "adx_period": MODEL_ADX_PERIOD,
        "adx_min_exclusive": MODEL_9_ADX_MIN if spec.requires_adx else None,
        "atr_period": MODEL_ATR_PERIOD,
        "distance_atr_min": (
            MODEL_10_DISTANCE_ATR_MIN if spec.requires_distance_atr else None
        ),
        "sma50_slope_lookback": (
            MODEL_11_SLOPE_LOOKBACK if spec.requires_sma50_slope else None
        ),
        "sma50_slope_atr_min": (
            MODEL_11_SLOPE_ATR_MIN if spec.requires_sma50_slope else None
        ),
        "entry_order_type": "MARKET_ON_CONFIRMED_CLOSED_M5_SMA20_50_CROSS_WITH_RSI50",
        "initial_entry_requires_fresh_sma_cross": True,
        "reentry_order_type": "PENDING_STOP_PREVIOUS_CLOSED_M5_EXTREME",
        "buy_reentry_trigger": "PREVIOUS_CLOSED_M5_HIGH_EXACT",
        "sell_reentry_trigger": "PREVIOUS_CLOSED_M5_LOW_EXACT",
        "reentry_requires_opposite_pullback_structure": True,
        "buy_reentry_pullback": "TWO_CLOSED_M5_LOWER_HIGHS_AND_LOWER_LOWS",
        "sell_reentry_pullback": "TWO_CLOSED_M5_HIGHER_HIGHS_AND_HIGHER_LOWS",
        "stop": "PIVOT_2X2_PLUS_0.01",
        "take_profit_enabled": spec.reentry_structural_target,
        "initial_take_profit_enabled": False,
        "reentry_take_profit_points": None,
        "reentry_take_profit_mode": (
            XAU_REENTRY_TARGET_MODE if spec.reentry_structural_target else None
        ),
        "reentry_buy_take_profit": "LAST_CONFIRMED_M5_SWING_HIGH_BEFORE_PULLBACK",
        "reentry_sell_take_profit": "LAST_CONFIRMED_M5_SWING_LOW_BEFORE_PULLBACK",
        "pending_stop_validity": "ONE_M5_CANDLE",
        "pending_stop_reposition": "EACH_NEW_CLOSED_M5_CANDLE",
        "max_reentries_per_signal": spec.max_reentries_per_signal,
        "reentries_unlimited_while_trend_valid": spec.max_reentries_per_signal is None,
        "source_model_id": spec.source_model_id,
        "full_exit": "REENTRY_RSI50_INVALIDATION_OR_SMA20_50_INVERSION",
    }


def is_improved_reentry_model(model_id: object) -> bool:
    return str(model_id or "").upper() in XAU_IMPROVED_REENTRY_MODEL_IDS


def xau_reentry_target(
    model_id: object,
    side: object,
    entry_price: float,
    entry_order_type: object,
    structural_target_price: object = None,
) -> float:
    """Retorna o topo/fundo confirmado anterior a correcao da reentrada."""
    spec = trend_filter_spec(model_id)
    order_type = str(entry_order_type or "").upper()
    if spec is None or not spec.reentry_structural_target or order_type not in {
        "BUY_STOP",
        "SELL_STOP",
    }:
        return 0.0
    try:
        target = float(structural_target_price or 0.0)
    except (TypeError, ValueError):
        return 0.0
    normalized_side = str(side or "").upper()
    if normalized_side == "BUY" and target > float(entry_price):
        return target
    if normalized_side == "SELL" and 0.0 < target < float(entry_price):
        return target
    return 0.0


def xau_model_requires_target(
    model_id: object,
    entry_order_type: object,
) -> bool:
    return is_improved_reentry_model(model_id) and str(
        entry_order_type or ""
    ).upper() in {"BUY_STOP", "SELL_STOP"}


def _filter_code(spec: XAUTrendFilterSpec) -> str:
    if spec.requires_adx and spec.requires_distance_atr and spec.requires_sma50_slope:
        return "FILTROS_COMBINADOS"
    if spec.requires_adx:
        return "ADX"
    if spec.requires_distance_atr:
        return "DISTANCIA_ATR"
    if spec.requires_sma50_slope:
        return "INCLINACAO_SMA50"
    return "BASE"


def _series(rows: list[object], field: str) -> list[float]:
    parsed = [_candle_value(row, field) for row in rows]
    return [float(value) for value in parsed if value is not None]


def _wilder_atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int,
) -> float:
    if len(closes) <= period or len(highs) != len(closes) or len(lows) != len(closes):
        return 0.0
    true_ranges = [
        max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1]))
        for index in range(1, len(closes))
    ]
    value = sum(true_ranges[:period]) / float(period)
    for current in true_ranges[period:]:
        value = ((value * (period - 1)) + current) / float(period)
    return value


def _wilder_adx(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int,
) -> float:
    if len(closes) < (period * 2 + 1) or len(highs) != len(closes) or len(lows) != len(closes):
        return 0.0
    true_ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for index in range(1, len(closes)):
        up = highs[index] - highs[index - 1]
        down = lows[index - 1] - lows[index]
        plus_dm.append(up if up > down and up > 0.0 else 0.0)
        minus_dm.append(down if down > up and down > 0.0 else 0.0)
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus = sum(plus_dm[:period])
    smoothed_minus = sum(minus_dm[:period])
    dx_values: list[float] = []
    for index in range(period, len(true_ranges)):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + true_ranges[index]
        smoothed_plus = smoothed_plus - (smoothed_plus / period) + plus_dm[index]
        smoothed_minus = smoothed_minus - (smoothed_minus / period) + minus_dm[index]
        plus_di = 100.0 * smoothed_plus / smoothed_tr if smoothed_tr else 0.0
        minus_di = 100.0 * smoothed_minus / smoothed_tr if smoothed_tr else 0.0
        total = plus_di + minus_di
        dx_values.append(100.0 * abs(plus_di - minus_di) / total if total else 0.0)
    if len(dx_values) < period:
        return 0.0
    adx = sum(dx_values[:period]) / float(period)
    for dx in dx_values[period:]:
        adx = ((adx * (period - 1)) + dx) / float(period)
    return adx
