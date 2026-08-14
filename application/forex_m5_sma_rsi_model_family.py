"""Familia M13-M17: SMA20/50 + RSI14 nos 17 pares Forex em M5."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from application.model8_xau_m5_sma_rsi_reentry import (
    Model8EntryDecision,
    evaluate_model8_entry,
    evaluate_model8_exit,
    evaluate_model8_native_entry,
    load_model8_runtime_state,
    update_model8_runtime_state,
    _sma,
)
from application.operational_indicator_window import OPERATIONAL_INDICATOR_RAW_CANDLES
from application.mt5_native_m5_indicators import MT5NativeM5IndicatorSnapshot
from application.xau_m5_sma_rsi_model_family import (
    MODEL_ADX_PERIOD,
    MODEL_ATR_PERIOD,
    MODEL_9_ADX_MIN,
    MODEL_10_DISTANCE_ATR_MIN,
    MODEL_11_SLOPE_ATR_MIN,
    MODEL_11_SLOPE_LOOKBACK,
    _series,
    _wilder_adx,
    _wilder_atr,
)
from domain.market_universe import MODEL_3_ALL_FOREX_PAIRS


MODEL_13_ID = "MODELO_13_FOREX_M5_SMA_RSI_REENTRY"
MODEL_14_ID = "MODELO_14_FOREX_M5_SMA_RSI_ADX"
MODEL_15_ID = "MODELO_15_FOREX_M5_SMA_RSI_MA_DISTANCE_ATR"
MODEL_16_ID = "MODELO_16_FOREX_M5_SMA_RSI_SMA50_SLOPE"
MODEL_17_ID = "MODELO_17_FOREX_M5_SMA_RSI_TREND_FILTERS"
FOREX_SMA_RSI_RETIRED_MODEL_IDS = (
    MODEL_13_ID,
    MODEL_14_ID,
    MODEL_15_ID,
)
FOREX_SMA_RSI_MODEL_IDS = (
    MODEL_16_ID,
    MODEL_17_ID,
)
FOREX_SMA_RSI_POSITION_MANAGEMENT_MODEL_IDS = (
    *FOREX_SMA_RSI_RETIRED_MODEL_IDS,
    *FOREX_SMA_RSI_MODEL_IDS,
)
FOREX_SMA_RSI_PAIRS = MODEL_3_ALL_FOREX_PAIRS
FOREX_SMA_RSI_TIMEFRAME = "M5"


@dataclass(frozen=True)
class ForexSmaRsiSpec:
    model_id: str
    number: int
    setup: str
    alpha_id: str
    alpha_version: str
    beta_id: str
    beta_version: str
    source: str
    stop_management: str
    requires_adx: bool = False
    requires_distance_atr: bool = False
    requires_sma50_slope: bool = False

    @property
    def comment(self) -> str:
        return f"TraderIA M{self.number}"


FOREX_SMA_RSI_SPECS = {
    MODEL_13_ID: ForexSmaRsiSpec(
        MODEL_13_ID, 13, "A", "ALPHAFX13_SMA_RSI", "M13_ENTRY_V1",
        "BETAFX13_RSI70_30_SMA_FULL_EXIT", "M13_EXIT_V1",
        "MODEL_13_FOREX_MANUAL_RULE", "M13_FOREX_SMA_RSI_FULL_EXIT",
    ),
    MODEL_14_ID: ForexSmaRsiSpec(
        MODEL_14_ID, 14, "B", "ALPHAFX14_SMA_RSI_ADX", "M14_ENTRY_V1",
        "BETAFX14_RSI70_30_SMA_FULL_EXIT", "M14_EXIT_V1",
        "MODEL_14_FOREX_MANUAL_RULE", "M14_FOREX_SMA_RSI_FULL_EXIT",
        requires_adx=True,
    ),
    MODEL_15_ID: ForexSmaRsiSpec(
        MODEL_15_ID, 15, "C", "ALPHAFX15_SMA_RSI_DISTANCE_ATR", "M15_ENTRY_V1",
        "BETAFX15_RSI70_30_SMA_FULL_EXIT", "M15_EXIT_V1",
        "MODEL_15_FOREX_MANUAL_RULE", "M15_FOREX_SMA_RSI_FULL_EXIT",
        requires_distance_atr=True,
    ),
    MODEL_16_ID: ForexSmaRsiSpec(
        MODEL_16_ID, 16, "D", "ALPHAFX16_SMA_RSI_SMA50_SLOPE", "M16_ENTRY_V1",
        "BETAFX16_RSI70_30_SMA_FULL_EXIT", "M16_EXIT_V1",
        "MODEL_16_FOREX_MANUAL_RULE", "M16_FOREX_SMA_RSI_FULL_EXIT",
        requires_sma50_slope=True,
    ),
    MODEL_17_ID: ForexSmaRsiSpec(
        MODEL_17_ID, 17, "E", "ALPHAFX17_SMA_RSI_TREND_FILTERS", "M17_ENTRY_V1",
        "BETAFX17_RSI70_30_SMA_FULL_EXIT", "M17_EXIT_V1",
        "MODEL_17_FOREX_MANUAL_RULE", "M17_FOREX_SMA_RSI_FULL_EXIT",
        requires_adx=True, requires_distance_atr=True, requires_sma50_slope=True,
    ),
}


@dataclass(frozen=True)
class ForexSmaRsiDecision:
    model_id: str
    pair: str
    setup: str
    base: Model8EntryDecision
    filter_allowed: bool
    status: str
    reason: str
    adx14: float | None = None
    atr14: float | None = None
    distance_atr: float | None = None
    sma50_slope_atr: float | None = None
    passed_filters: tuple[str, ...] = ()
    failed_filters: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.base.ready and self.filter_allowed


def forex_sma_rsi_spec(model_id: object) -> ForexSmaRsiSpec | None:
    return FOREX_SMA_RSI_SPECS.get(str(model_id or "").upper())


def forex_pip_size(pair: object) -> float:
    return 0.01 if str(pair or "").upper().endswith("JPY") else 0.0001


def evaluate_forex_sma_rsi_entry(
    model_id: str,
    pair: str,
    candles: Iterable[object],
    *,
    awaiting_reentry_side: str | None = None,
) -> ForexSmaRsiDecision:
    spec = forex_sma_rsi_spec(model_id)
    normalized_pair = str(pair or "").upper()
    if spec is None:
        raise ValueError(f"Modelo Forex SMA/RSI desconhecido: {model_id}")
    if normalized_pair not in FOREX_SMA_RSI_PAIRS:
        base = Model8EntryDecision(
            direction="WAIT",
            status=f"M{spec.number}_PAIR_OUTSIDE_MODEL_SCOPE",
            reason=f"M{spec.number} nao opera {normalized_pair or 'N/D'}.",
        )
        return ForexSmaRsiDecision(
            spec.model_id, normalized_pair, spec.setup, base, False,
            base.status, base.reason, failed_filters=("PAIR_SCOPE",),
        )
    rows = list(candles or ())
    required_rows = OPERATIONAL_INDICATOR_RAW_CANDLES
    if len(rows) < required_rows:
        status = f"M{spec.number}_AQUECENDO_{len(rows)}_DE_{required_rows}_CANDLES"
        base = replace(evaluate_model8_entry(rows), status=status)
        reason = (
            f"M{spec.number} {normalized_pair} recebeu {len(rows)} de "
            f"{required_rows} candles M5 necessarios."
        )
        return ForexSmaRsiDecision(
            spec.model_id, normalized_pair, spec.setup, base, False,
            status, reason, failed_filters=("CANDLE_WARMUP",),
        )
    base = evaluate_model8_entry(
        rows,
        awaiting_reentry_side=awaiting_reentry_side,
        stop_buffer=forex_pip_size(normalized_pair),
    )
    closed_rows = rows[:-1]
    highs = _series(closed_rows, "high")
    lows = _series(closed_rows, "low")
    closes = _series(closed_rows, "close")
    atr14 = _wilder_atr(highs, lows, closes, MODEL_ATR_PERIOD)
    adx14 = _wilder_adx(highs, lows, closes, MODEL_ADX_PERIOD)
    distance_atr = (
        abs(float(base.sma20 or 0.0) - float(base.sma50 or 0.0)) / atr14
        if atr14 > 0.0 else 0.0
    )
    current_sma50 = _sma(closes, 50)
    earlier_sma50 = _sma(closes[:-MODEL_11_SLOPE_LOOKBACK], 50)
    raw_slope = current_sma50 - earlier_sma50
    direction = (
        base.direction if base.direction in {"BUY", "SELL"}
        else "BUY" if float(base.sma20 or 0.0) > float(base.sma50 or 0.0)
        else "SELL"
    )
    directional_slope = raw_slope if direction == "BUY" else -raw_slope
    slope_atr = directional_slope / atr14 if atr14 > 0.0 else 0.0

    passed: list[str] = []
    failed: list[str] = []
    if spec.requires_adx:
        (passed if adx14 > MODEL_9_ADX_MIN else failed).append("ADX14>25")
    if spec.requires_distance_atr:
        (passed if distance_atr >= MODEL_10_DISTANCE_ATR_MIN else failed).append(
            "DISTANCE_ATR>=0.25"
        )
    if spec.requires_sma50_slope:
        (passed if slope_atr >= MODEL_11_SLOPE_ATR_MIN else failed).append(
            "SMA50_SLOPE_ATR>=0.05"
        )
    filter_code = {
        13: "BASE", 14: "ADX", 15: "DISTANCIA_ATR",
        16: "INCLINACAO_SMA50", 17: "FILTROS_COMBINADOS",
    }[spec.number]
    allowed = not failed
    if failed:
        status = f"M{spec.number}_{filter_code}_BLOQUEADO"
        reason = f"Setup {spec.setup} bloqueado: {', '.join(failed)}. {base.reason}"
    elif base.ready:
        order_label = base.entry_order_type or "MARKET"
        status = f"M{spec.number}_{filter_code}_OK_{base.direction}_{order_label}_PRONTA"
        reason = f"Setup {spec.setup} liberado em {normalized_pair}. {base.reason}"
    else:
        status = f"M{spec.number}_{filter_code}_OK_{base.status.removeprefix('M8_')}"
        reason = f"Setup {spec.setup}: filtros aprovados. {base.reason}"
    return ForexSmaRsiDecision(
        spec.model_id, normalized_pair, spec.setup,
        replace(base, status=status, reason=reason), allowed, status, reason,
        adx14=adx14, atr14=atr14, distance_atr=distance_atr,
        sma50_slope_atr=slope_atr, passed_filters=tuple(passed),
        failed_filters=tuple(failed),
    )


def evaluate_forex_native_sma_rsi_entry(
    model_id: str,
    pair: str,
    snapshot: MT5NativeM5IndicatorSnapshot,
    *,
    awaiting_reentry_side: str | None = None,
) -> ForexSmaRsiDecision:
    """Decide M13-M17 sem warmup Python, usando o pacote nativo do MT5."""
    spec = forex_sma_rsi_spec(model_id)
    normalized_pair = str(pair or "").upper()
    if spec is None:
        raise ValueError(f"Modelo Forex SMA/RSI desconhecido: {model_id}")
    base = evaluate_model8_native_entry(
        snapshot,
        awaiting_reentry_side=awaiting_reentry_side,
        stop_buffer=forex_pip_size(normalized_pair),
    )
    direction = (
        base.direction
        if base.direction in {"BUY", "SELL"}
        else "BUY" if snapshot.sma20 > snapshot.sma50 else "SELL"
    )
    slope_atr = snapshot.sma50_slope_atr if direction == "BUY" else -snapshot.sma50_slope_atr
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
    filter_code = {
        13: "BASE", 14: "ADX", 15: "DISTANCIA_ATR",
        16: "INCLINACAO_SMA50", 17: "FILTROS_COMBINADOS",
    }[spec.number]
    allowed = not failed
    if failed:
        status = f"M{spec.number}_{filter_code}_BLOQUEADO"
        reason = f"MT5 nativo, Setup {spec.setup} bloqueado: {', '.join(failed)}."
    elif base.ready:
        status = f"M{spec.number}_{filter_code}_OK_{base.direction}_{base.entry_order_type}_PRONTA"
        reason = f"MT5 nativo, Setup {spec.setup} liberado em {normalized_pair}."
    else:
        status = f"M{spec.number}_{filter_code}_OK_{base.status.removeprefix('M8_')}"
        reason = f"MT5 nativo, filtros aprovados. {base.reason}"
    return ForexSmaRsiDecision(
        spec.model_id, normalized_pair, spec.setup,
        replace(base, status=status, reason=reason), allowed, status, reason,
        adx14=snapshot.adx14, atr14=snapshot.atr14,
        distance_atr=snapshot.distance_atr, sma50_slope_atr=slope_atr,
        passed_filters=tuple(passed), failed_filters=tuple(failed),
    )


def forex_sma_rsi_parameters(model_id: str, pair: str) -> dict[str, object]:
    spec = forex_sma_rsi_spec(model_id)
    if spec is None:
        raise ValueError(f"Modelo Forex SMA/RSI desconhecido: {model_id}")
    pip = forex_pip_size(pair)
    return {
        "setup": spec.setup,
        "pair": str(pair or "").upper(),
        "scope": FOREX_SMA_RSI_PAIRS,
        "timeframe": FOREX_SMA_RSI_TIMEFRAME,
        "sma_fast": 20, "sma_slow": 50, "rsi_period": 14,
        "entry_rsi_level": 50.0,
        "adx_period": 14,
        "adx_min_exclusive": 25.0 if spec.requires_adx else None,
        "atr_period": 14,
        "distance_atr_min": 0.25 if spec.requires_distance_atr else None,
        "sma50_slope_lookback": 1 if spec.requires_sma50_slope else None,
        "sma50_slope_atr_min": 0.05 if spec.requires_sma50_slope else None,
        "pip_size": pip,
        "initial_entry_order_type": "MARKET_ON_CONFIRMED_CLOSED_M5_SMA20_50_CROSS",
        "initial_entry_requires_fresh_sma_cross": True,
        "reentry_order_type": "BUY_STOP_OR_SELL_STOP_AT_PREVIOUS_CANDLE_EXTREME_EXACT",
        "stop": "PIVOT_2X2_PLUS_ONE_PIP",
        "take_profit_enabled": False,
        "full_exit": "RSI70_30_CONFIRMED_CROSS_OR_SMA20_50_INVERSION",
    }


def forex_runtime_state_path(model_id: str, pair: str) -> Path:
    spec = forex_sma_rsi_spec(model_id)
    if spec is None:
        raise ValueError(f"Modelo Forex SMA/RSI desconhecido: {model_id}")
    normalized_pair = str(pair or "").upper()
    return Path(".traderia") / f"model{spec.number}_{normalized_pair}_runtime_state.json"


def load_forex_sma_rsi_runtime_state(model_id: str, pair: str) -> dict[str, object]:
    return load_model8_runtime_state(
        forex_runtime_state_path(model_id, pair), operational_model=model_id,
    )


def update_forex_sma_rsi_runtime_state(
    model_id: str,
    pair: str,
    **changes: object,
) -> dict[str, object]:
    return update_model8_runtime_state(
        path=forex_runtime_state_path(model_id, pair),
        operational_model=model_id,
        symbol=str(pair or "").upper(),
        **changes,
    )


evaluate_forex_sma_rsi_exit = evaluate_model8_exit
