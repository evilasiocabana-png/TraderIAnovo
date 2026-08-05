"""Mechanical M2 trend-pullback contract for MT5 Demo."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


MODEL_2_ALPHA_ID = "ALPHA_M2_TREND_PULLBACK"
MODEL_2_FAMILY = "TREND_PULLBACK_M15_H1"
MODEL_2_ENTRY_TIMEFRAME = "M15"
MODEL_2_CONTEXT_TIMEFRAME = "H1"
MODEL_2_PAIRS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)
MODEL_2_PARAMETERS: dict[str, Any] = {
    "family": MODEL_2_FAMILY,
    "entry_timeframe": MODEL_2_ENTRY_TIMEFRAME,
    "context_timeframe": MODEL_2_CONTEXT_TIMEFRAME,
    "fast": 9,
    "slow": 21,
    "context_fast": 20,
    "context_slow": 50,
    "adx_period": 14,
    "adx_min": 20.0,
    "atr_period": 14,
    "stop_factor": 1.25,
    "risk_reward": 2.0,
    "pullback_rule": "PREVIOUS_CANDLE_OVERLAPS_EMA_BAND",
    "confirmation_rule": "CLOSED_CANDLE_RESUMES_TREND",
    "entry_contract": "NEXT_LIVE_PRICE_AFTER_M15_CLOSE",
    "exit_policy": "FIXED_SL_TP",
}


def trend_pullback_parameters(
    *,
    family: str,
    entry_timeframe: str,
    context_timeframe: str,
) -> dict[str, Any]:
    """Build one M2-compatible contract for a different timeframe pair."""
    parameters = dict(MODEL_2_PARAMETERS)
    parameters.update(
        {
            "family": str(family).upper(),
            "entry_timeframe": str(entry_timeframe).upper(),
            "context_timeframe": str(context_timeframe).upper(),
            "entry_contract": (
                "NEXT_LIVE_PRICE_AFTER_"
                f"{str(entry_timeframe).upper()}_CLOSE"
            ),
        }
    )
    return parameters


@dataclass(frozen=True)
class Model2TrendPullbackReading:
    direction: int
    atr: float
    diagnostics: tuple[str, ...]


def model2_operational_results() -> dict[str, dict[str, Any]]:
    """Return the same traceable M2 contract for every monitored Forex pair."""
    return {
        pair: {
            "pair": pair,
            "alpha_id": MODEL_2_ALPHA_ID,
            "timeframe": MODEL_2_ENTRY_TIMEFRAME,
            "source_model": "M2",
            "entry_contract": MODEL_2_PARAMETERS["entry_contract"],
            "demo_forward_enabled": True,
            "parity_status": "DEMO_FORWARD_OPERATIONALLY_APPROVED",
            "parity_reason": (
                "M2 Trend Pullback aprovado pelo usuario para execucao MT5 Demo."
            ),
            "evidence_demo_forward_enabled": False,
            "evidence_parity_status": "REPLAY_VALIDATION_PENDING",
            "evidence_parity_reason": (
                "Contrato operacional aprovado; desempenho ainda exige replay "
                "e forward test separados por par."
            ),
            "parameters": dict(MODEL_2_PARAMETERS),
            "context_overlay": {
                "h1_mode": "EMA20_50_DIRECTION",
            },
            "holdout_next_open": {},
        }
        for pair in MODEL_2_PAIRS
    }


def trend_pullback_operational_results(
    *,
    model_label: str,
    alpha_id: str,
    family: str,
    entry_timeframe: str,
    context_timeframe: str,
    mirror_source_model: str | None = None,
    mirror_swap_sl_tp: bool = False,
) -> dict[str, dict[str, Any]]:
    """Create a traceable Demo contract for an M2 timeframe variant."""
    label = str(model_label).upper()
    parameters = trend_pullback_parameters(
        family=family,
        entry_timeframe=entry_timeframe,
        context_timeframe=context_timeframe,
    )
    if mirror_swap_sl_tp:
        source_stop_factor = float(parameters["stop_factor"])
        source_risk_reward = float(parameters["risk_reward"])
        parameters.update(
            {
                "stop_factor": source_stop_factor * source_risk_reward,
                "risk_reward": 1.0 / source_risk_reward,
                "mirror_source_model": str(mirror_source_model or "N/D").upper(),
                "mirror_swap_sl_tp": True,
                "mirror_source_stop_factor": source_stop_factor,
                "mirror_source_risk_reward": source_risk_reward,
            }
        )
    return {
        pair: {
            "pair": pair,
            "alpha_id": str(alpha_id).upper(),
            "timeframe": str(entry_timeframe).upper(),
            "source_model": label,
            "entry_contract": parameters["entry_contract"],
            "demo_forward_enabled": True,
            "parity_status": "DEMO_FORWARD_OPERATIONALLY_APPROVED",
            "parity_reason": (
                f"{label} espelha {str(mirror_source_model).upper()} com "
                "direcao e SL/TP invertidos para execucao MT5 Demo."
                if mirror_swap_sl_tp
                else (
                    f"{label} Trend Pullback {context_timeframe}->{entry_timeframe} "
                    "aprovado pelo usuario para execucao MT5 Demo."
                )
            ),
            "evidence_demo_forward_enabled": False,
            "evidence_parity_status": "REPLAY_VALIDATION_PENDING",
            "evidence_parity_reason": (
                "Variante operacional do M2; desempenho ainda exige replay "
                "e forward test separados por par."
            ),
            "parameters": dict(parameters),
            "context_overlay": {
                "direction_mode": (
                    f"{str(context_timeframe).upper()}_EMA20_50_DIRECTION"
                ),
            },
            "holdout_next_open": {},
        }
        for pair in MODEL_2_PAIRS
    }


def evaluate_model2_trend_pullback(
    entry_candles: Sequence[Mapping[str, Any]],
    context_candles: Sequence[Mapping[str, Any]],
    parameters: Mapping[str, Any] | None = None,
) -> Model2TrendPullbackReading:
    """Evaluate the last closed M15 candle against the last closed H1 context."""
    return evaluate_trend_pullback(
        entry_candles,
        context_candles,
        parameters,
        model_label="M2",
    )


def evaluate_trend_pullback(
    entry_candles: Sequence[Mapping[str, Any]],
    context_candles: Sequence[Mapping[str, Any]],
    parameters: Mapping[str, Any] | None = None,
    *,
    model_label: str = "M2",
) -> Model2TrendPullbackReading:
    """Evaluate the last closed entry candle against its direction context."""
    configured = {**MODEL_2_PARAMETERS, **dict(parameters or {})}
    entry_timeframe = str(configured.get("entry_timeframe") or "M15").upper()
    context_timeframe = str(configured.get("context_timeframe") or "H1").upper()
    label = str(model_label or "M2").upper()
    entry = _indicator_frame(
        entry_candles,
        fast=int(configured["fast"]),
        slow=int(configured["slow"]),
        adx_period=int(configured["adx_period"]),
        atr_period=int(configured["atr_period"]),
    )
    context = _indicator_frame(
        context_candles,
        fast=int(configured["context_fast"]),
        slow=int(configured["context_slow"]),
        adx_period=int(configured["adx_period"]),
        atr_period=int(configured["atr_period"]),
    )
    if len(entry.index) < 2 or len(context.index) < 1:
        raise ValueError(
            f"Candles insuficientes para avaliar {label} Trend Pullback."
        )

    confirmation = entry.iloc[-1]
    pullback = entry.iloc[-2]
    direction_context = context.iloc[-1]
    fast_name = f"ema{int(configured['fast'])}"
    slow_name = f"ema{int(configured['slow'])}"
    context_fast_name = f"ema{int(configured['context_fast'])}"
    context_slow_name = f"ema{int(configured['context_slow'])}"

    required = (
        confirmation[fast_name],
        confirmation[slow_name],
        confirmation["adx"],
        confirmation["atr"],
        pullback[fast_name],
        pullback[slow_name],
        direction_context[context_fast_name],
        direction_context[context_slow_name],
    )
    if not all(math.isfinite(float(value)) for value in required):
        raise ValueError(
            f"Indicadores {label} ainda nao possuem janela completa."
        )

    band_low = min(float(pullback[fast_name]), float(pullback[slow_name]))
    band_high = max(float(pullback[fast_name]), float(pullback[slow_name]))
    touched_band = (
        float(pullback["low"]) <= band_high
        and float(pullback["high"]) >= band_low
    )
    context_buy = float(direction_context[context_fast_name]) > float(
        direction_context[context_slow_name]
    )
    context_sell = float(direction_context[context_fast_name]) < float(
        direction_context[context_slow_name]
    )
    entry_buy = float(confirmation[fast_name]) > float(confirmation[slow_name])
    entry_sell = float(confirmation[fast_name]) < float(confirmation[slow_name])
    adx_ok = float(confirmation["adx"]) > float(configured["adx_min"])
    bullish_confirmation = (
        float(confirmation["close"]) > float(confirmation["open"])
        and float(confirmation["close"]) > float(confirmation[fast_name])
    )
    bearish_confirmation = (
        float(confirmation["close"]) < float(confirmation["open"])
        and float(confirmation["close"]) < float(confirmation[fast_name])
    )

    direction = 0
    if context_buy and entry_buy and adx_ok and touched_band and bullish_confirmation:
        direction = 1
    elif context_sell and entry_sell and adx_ok and touched_band and bearish_confirmation:
        direction = -1

    context_trend = "BUY" if context_buy else "SELL" if context_sell else "FLAT"
    entry_trend = "BUY" if entry_buy else "SELL" if entry_sell else "FLAT"
    signal = "BUY" if direction > 0 else "SELL" if direction < 0 else "WAIT"
    diagnostics = (
        f"{entry_timeframe}_EMA{configured['fast']}={float(confirmation[fast_name]):.6f}",
        f"{entry_timeframe}_EMA{configured['slow']}={float(confirmation[slow_name]):.6f}",
        f"ADX{configured['adx_period']}={float(confirmation['adx']):.6f}",
        f"ATR{configured['atr_period']}={float(confirmation['atr']):.6f}",
        f"PULLBACK_TOUCH={int(touched_band)}",
        f"CONFIRM_BULLISH={int(bullish_confirmation)}",
        f"CONFIRM_BEARISH={int(bearish_confirmation)}",
        f"{context_timeframe}_EMA{configured['context_fast']}={float(direction_context[context_fast_name]):.6f}",
        f"{context_timeframe}_EMA{configured['context_slow']}={float(direction_context[context_slow_name]):.6f}",
        f"{context_timeframe}_TREND={context_trend}",
        f"{entry_timeframe}_TREND={entry_trend}",
        f"{label}_SIGNAL={signal}",
    )
    return Model2TrendPullbackReading(
        direction=direction,
        atr=float(confirmation["atr"]),
        diagnostics=diagnostics,
    )


def _indicator_frame(
    candles: Sequence[Mapping[str, Any]],
    *,
    fast: int,
    slow: int,
    adx_period: int,
    atr_period: int,
) -> pd.DataFrame:
    frame = pd.DataFrame(list(candles)).rename(
        columns={
            "abertura": "open",
            "maxima": "high",
            "minima": "low",
            "fechamento": "close",
        }
    )
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for period in {fast, slow}:
        frame[f"ema{period}"] = frame["close"].ewm(
            span=period,
            adjust=False,
            min_periods=period,
        ).mean()

    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        (
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)
    frame["atr"] = true_range.ewm(
        alpha=1 / atr_period,
        adjust=False,
        min_periods=atr_period,
    ).mean()
    upward = frame["high"].diff()
    downward = -frame["low"].diff()
    plus_dm = pd.Series(
        np.where((upward > downward) & (upward > 0), upward, 0.0),
        index=frame.index,
    )
    minus_dm = pd.Series(
        np.where((downward > upward) & (downward > 0), downward, 0.0),
        index=frame.index,
    )
    smoothed_range = true_range.ewm(
        alpha=1 / adx_period,
        adjust=False,
        min_periods=adx_period,
    ).mean()
    plus_di = 100 * plus_dm.ewm(
        alpha=1 / adx_period,
        adjust=False,
        min_periods=adx_period,
    ).mean() / smoothed_range
    minus_di = 100 * minus_dm.ewm(
        alpha=1 / adx_period,
        adjust=False,
        min_periods=adx_period,
    ).mean() / smoothed_range
    directional_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / directional_sum
    frame["adx"] = dx.ewm(
        alpha=1 / adx_period,
        adjust=False,
        min_periods=adx_period,
    ).mean()
    return frame
