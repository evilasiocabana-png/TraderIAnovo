"""Search robust, explainable Alpha candidates independently for each pair.

The experiment is intentionally isolated from the operational runtime. Candidate
selection uses only the development window and four chronological stability
blocks. The final holdout is opened after one winner per pair is frozen.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from research.alpha_suggested.alpha_suggested_1_plus_discovery import (
    MarketArrays,
    _as_bool,
    engineer_features,
)
from research.traderia_certification_index import (
    TraderIACertificationEngine,
    TraderIACertificationInput,
)


ALPHA_ID = "ALPHA_SUGERIDA_002_PLUS"
MODEL_DESTINATION = "MODELO_3"
TIMEFRAME = "H1"
DEFAULT_ROUND_TRIP_COST_BPS = 1.5
STRESS_ROUND_TRIP_COST_BPS = 2.5
MINIMUM_DISTANCE_PERCENT = 0.0005


@dataclass(frozen=True)
class ResearchWindows:
    development: tuple[int, int]
    stability_blocks: tuple[tuple[int, int], ...]
    holdout: tuple[int, int]


def chronological_research_windows(candle_count: int) -> ResearchWindows:
    """Reserve the newest 20 percent and split development into four blocks."""
    safe_count = max(int(candle_count), 0)
    development_end = int(safe_count * 0.80)
    block_size = development_end // 4
    blocks = tuple(
        (
            index * block_size,
            development_end if index == 3 else (index + 1) * block_size,
        )
        for index in range(4)
    )
    return ResearchWindows(
        development=(0, development_end),
        stability_blocks=blocks,
        holdout=(development_end, safe_count),
    )


def load_markets_for_timeframe(
    snapshot_path: Path,
    timeframe: str,
) -> dict[str, MarketArrays]:
    normalized_timeframe = str(timeframe).strip().upper()
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    markets: dict[str, MarketArrays] = {}
    for key, candles in payload.get("candles_by_market", {}).items():
        pair, stored_timeframe = str(key).split("|", maxsplit=1)
        if stored_timeframe.upper() != normalized_timeframe:
            continue
        markets[pair.upper()] = engineer_features(pair.upper(), list(candles))
    if not markets:
        raise RuntimeError(
            f"No {normalized_timeframe} markets found in {snapshot_path}."
        )
    return markets


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + relative_strength))


def enrich_market(market: MarketArrays) -> MarketArrays:
    """Add the feature library used only by the isolated M3 experiment."""
    frame = market.frame
    close = frame["close"]
    atr = frame["atr14"].replace(0, np.nan)
    for period in (8, 13, 21, 34, 55, 89, 144, 200):
        name = f"ema{period}"
        if name not in frame:
            frame[name] = close.ewm(
                span=period,
                adjust=False,
                min_periods=period,
            ).mean()
    frame["rsi7"] = _rsi(close, 7)
    frame["rsi14"] = frame["rsi"]
    frame["rsi21"] = _rsi(close, 21)
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd"] = ema12 - ema26
    frame["macd_signal"] = frame["macd"].ewm(
        span=9,
        adjust=False,
        min_periods=9,
    ).mean()
    frame["macd_hist_atr"] = (frame["macd"] - frame["macd_signal"]) / atr
    frame["macd_hist_delta"] = frame["macd_hist_atr"].diff(2)
    mean20 = close.rolling(20, min_periods=20).mean()
    std20 = close.rolling(20, min_periods=20).std().replace(0, np.nan)
    frame["zscore20"] = (close - mean20) / std20
    frame["bb_width_atr"] = (4 * std20) / atr
    frame["bb_width_ratio"] = frame["bb_width_atr"] / frame[
        "bb_width_atr"
    ].rolling(100, min_periods=50).mean()
    for period in (1, 3, 6, 12):
        frame[f"roc_{period}"] = close / close.shift(period) - 1
    for period in (10, 30):
        frame[f"efficiency_{period}"] = (
            (close - close.shift(period)).abs()
            / close.diff().abs().rolling(period, min_periods=period).sum().replace(0, np.nan)
        )
    for period in (10, 20, 40, 60):
        frame[f"prior_high_{period}"] = frame["high"].shift(1).rolling(
            period,
            min_periods=period,
        ).max()
        frame[f"prior_low_{period}"] = frame["low"].shift(1).rolling(
            period,
            min_periods=period,
        ).min()
    for period in (8, 13, 21, 34, 55, 89, 144, 200):
        frame[f"ema{period}_slope_atr"] = (
            frame[f"ema{period}"] - frame[f"ema{period}"].shift(3)
        ) / atr
    return market


def _common_context_mask(
    frame: pd.DataFrame,
    candidate: dict[str, Any],
    signal: np.ndarray,
) -> np.ndarray:
    mask = np.ones(len(frame), dtype=bool)
    hours = frame["hour_utc"].to_numpy(dtype=float)
    weekdays = frame["weekday"].to_numpy(dtype=float)
    session = str(candidate.get("session", "ALL"))
    if session == "LONDON":
        mask &= (hours >= 7) & (hours < 12)
    elif session == "NEW_YORK":
        mask &= (hours >= 12) & (hours < 18)
    elif session == "ACTIVE":
        mask &= (hours >= 7) & (hours < 18)
    elif session == "OVERLAP":
        mask &= (hours >= 12) & (hours < 16)
    elif session == "ASIA":
        mask &= (hours >= 0) & (hours < 7)

    weekday_mode = str(candidate.get("weekdays", "ALL"))
    if weekday_mode == "MON_THU":
        mask &= weekdays <= 3
    elif weekday_mode == "TUE_THU":
        mask &= (weekdays >= 1) & (weekdays <= 3)
    elif weekday_mode == "NOT_MONDAY":
        mask &= weekdays >= 1

    atr_ratio = frame["atr_ratio"].to_numpy(dtype=float)
    atr_regime = str(candidate.get("atr_regime", "ALL"))
    if atr_regime == "QUIET":
        mask &= atr_ratio <= 0.92
    elif atr_regime == "NORMAL":
        mask &= (atr_ratio > 0.88) & (atr_ratio < 1.12)
    elif atr_regime == "EXPANDING":
        mask &= atr_ratio >= 1.08

    efficiency = frame[f"efficiency_{candidate['efficiency_period']}"]
    mask &= efficiency.to_numpy(dtype=float) >= float(candidate["efficiency_min"])
    efficiency_max = float(candidate.get("efficiency_max", 1.0))
    if efficiency_max < 1.0:
        mask &= efficiency.to_numpy(dtype=float) <= efficiency_max

    if bool(candidate.get("slope_aligned", False)):
        slope = frame[f"ema{candidate['slow']}_slope_atr"].to_numpy(dtype=float)
        mask &= ((signal > 0) & (slope > 0)) | ((signal < 0) & (slope < 0))
    return mask


def build_signal(market: MarketArrays, candidate: dict[str, Any]) -> np.ndarray:
    frame = market.frame
    family = str(candidate["family"])
    fast = frame[f"ema{candidate['fast']}"]
    slow = frame[f"ema{candidate['slow']}"]
    trend_buy = fast > slow
    trend_sell = fast < slow
    adx = frame["adx"]
    adx_ok = adx >= float(candidate.get("adx_min", 0.0))
    if bool(candidate.get("adx_rising", False)):
        adx_ok &= frame["adx_delta"] > 0
    volume_ok = frame["volume_ratio"] >= float(candidate.get("volume_min", 0.0))

    if family == "TREND_PULLBACK_CONTINUATION":
        tolerance = float(candidate["touch_atr"])
        atr = frame["atr14"]
        touched_buy = (frame["low"] <= fast + atr * tolerance) & (frame["close"] > fast)
        touched_sell = (frame["high"] >= fast - atr * tolerance) & (frame["close"] < fast)
        rsi = frame[f"rsi{candidate['rsi_period']}"]
        buy = (
            trend_buy
            & adx_ok
            & volume_ok
            & touched_buy
            & (frame["close"] > frame["open"])
            & (frame["lower_wick"] >= float(candidate["wick_min"]))
            & rsi.between(float(candidate["rsi_low"]), float(candidate["rsi_high"]))
            & (frame[f"roc_{candidate['roc_period']}"] > 0)
        )
        sell = (
            trend_sell
            & adx_ok
            & volume_ok
            & touched_sell
            & (frame["close"] < frame["open"])
            & (frame["upper_wick"] >= float(candidate["wick_min"]))
            & rsi.between(100 - float(candidate["rsi_high"]), 100 - float(candidate["rsi_low"]))
            & (frame[f"roc_{candidate['roc_period']}"] < 0)
        )
    elif family == "MOMENTUM_ACCELERATION":
        hist = frame["macd_hist_atr"]
        delta = frame["macd_hist_delta"]
        body_ok = frame["body_atr"] >= float(candidate["body_atr"])
        buy = (
            trend_buy
            & adx_ok
            & volume_ok
            & body_ok
            & (hist >= float(candidate["hist_min"]))
            & (delta > 0)
            & (frame[f"roc_{candidate['roc_period']}"] > float(candidate["roc_min"]))
            & (frame["close_position"] >= float(candidate["close_extreme"]))
        )
        sell = (
            trend_sell
            & adx_ok
            & volume_ok
            & body_ok
            & (hist <= -float(candidate["hist_min"]))
            & (delta < 0)
            & (frame[f"roc_{candidate['roc_period']}"] < -float(candidate["roc_min"]))
            & (frame["close_position"] <= 1 - float(candidate["close_extreme"]))
        )
    elif family == "BREAKOUT_EXPANSION":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        base = (
            adx_ok
            & volume_ok
            & (frame["range_atr"] >= float(candidate["range_atr"]))
        )
        buy = (
            base
            & (frame["close"] > prior_high)
            & (frame["close_position"] >= float(candidate["close_extreme"]))
        )
        sell = (
            base
            & (frame["close"] < prior_low)
            & (frame["close_position"] <= 1 - float(candidate["close_extreme"]))
        )
        if bool(candidate["trend_required"]):
            buy &= trend_buy
            sell &= trend_sell
    elif family == "SQUEEZE_RELEASE":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        squeeze = frame["bb_width_ratio"].shift(1) <= float(candidate["squeeze_max"])
        base = (
            squeeze
            & adx_ok
            & volume_ok
            & (frame["range_atr"] >= float(candidate["range_atr"]))
        )
        buy = base & (frame["close"] > prior_high)
        sell = base & (frame["close"] < prior_low)
        if bool(candidate["trend_required"]):
            buy &= trend_buy
            sell &= trend_sell
    elif family == "MEAN_REVERSION_REJECTION":
        rsi = frame[f"rsi{candidate['rsi_period']}"]
        adx_quiet = adx <= float(candidate["adx_max"])
        buy = (
            adx_quiet
            & volume_ok
            & (frame["zscore20"] <= -float(candidate["zscore_min"]))
            & (rsi <= float(candidate["rsi_extreme"]))
            & (frame["lower_wick"] >= float(candidate["wick_min"]))
            & (frame["close"] > frame["open"])
        )
        sell = (
            adx_quiet
            & volume_ok
            & (frame["zscore20"] >= float(candidate["zscore_min"]))
            & (rsi >= 100 - float(candidate["rsi_extreme"]))
            & (frame["upper_wick"] >= float(candidate["wick_min"]))
            & (frame["close"] < frame["open"])
        )
    elif family == "LIQUIDITY_RECLAIM":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        adx_quiet = adx <= float(candidate["adx_max"])
        buy = (
            adx_quiet
            & volume_ok
            & (frame["low"] < prior_low)
            & (frame["close"] > prior_low)
            & (frame["lower_wick"] >= float(candidate["wick_min"]))
            & (frame["rsi7"] <= float(candidate["rsi_extreme"]))
        )
        sell = (
            adx_quiet
            & volume_ok
            & (frame["high"] > prior_high)
            & (frame["close"] < prior_high)
            & (frame["upper_wick"] >= float(candidate["wick_min"]))
            & (frame["rsi7"] >= 100 - float(candidate["rsi_extreme"]))
        )
    elif family == "STRUCTURE_CONTINUATION":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        buffer = frame["atr14"] * float(candidate["reclaim_buffer_atr"])
        buy = (
            trend_buy
            & adx_ok
            & volume_ok
            & (frame["low"] <= prior_high + buffer)
            & (frame["close"] > prior_high)
            & (frame["close"] > frame["open"])
        )
        sell = (
            trend_sell
            & adx_ok
            & volume_ok
            & (frame["high"] >= prior_low - buffer)
            & (frame["close"] < prior_low)
            & (frame["close"] < frame["open"])
        )
    else:
        raise ValueError(f"Unknown family: {family}")

    signal = np.zeros(len(frame), dtype=np.int8)
    signal[_as_bool(buy)] = 1
    signal[_as_bool(sell)] = -1
    signal[~_common_context_mask(frame, candidate, signal)] = 0
    previous = np.concatenate((np.array([0], dtype=np.int8), signal[:-1]))
    signal[(signal != 0) & (signal == previous)] = 0
    return signal


def replay_segment(
    market: MarketArrays,
    signal: np.ndarray,
    bounds: tuple[int, int],
    *,
    stop_factor: float,
    risk_reward: float,
    round_trip_cost_fraction: float,
) -> list[dict[str, float]]:
    outcomes: list[dict[str, float]] = []
    start, requested_end = bounds
    index = max(int(start), 250)
    end = min(int(requested_end), len(market.close))
    while index < end - 1:
        direction = int(signal[index])
        atr = float(market.atr[index])
        entry = float(market.close[index])
        if direction == 0 or not math.isfinite(atr) or entry <= 0:
            index += 1
            continue
        distance = max(atr * stop_factor, abs(entry) * MINIMUM_DISTANCE_PERCENT)
        stop = entry - direction * distance
        target = entry + direction * distance * risk_reward
        future_high = market.high[index + 1 : end]
        future_low = market.low[index + 1 : end]
        if direction > 0:
            stop_hits = np.flatnonzero(future_low <= stop)
            target_hits = np.flatnonzero(future_high >= target)
        else:
            stop_hits = np.flatnonzero(future_high >= stop)
            target_hits = np.flatnonzero(future_low <= target)
        first_stop = int(stop_hits[0]) if stop_hits.size else None
        first_target = int(target_hits[0]) if target_hits.size else None
        if first_stop is None and first_target is None:
            break
        stop_first = first_stop is not None and (
            first_target is None or first_stop <= first_target
        )
        exit_offset = first_stop if stop_first else first_target
        if exit_offset is None:
            break
        risk_fraction = distance / abs(entry)
        gross_return = -risk_fraction if stop_first else risk_fraction * risk_reward
        outcomes.append(
            {
                "gross_return": gross_return,
                "net_return": gross_return - round_trip_cost_fraction,
                "duration_candles": float(exit_offset + 1),
            }
        )
        index = index + 2 + exit_offset
    return outcomes


def summarize_outcomes(outcomes: Iterable[dict[str, float]]) -> dict[str, Any]:
    rows = list(outcomes)
    net = np.asarray([row["net_return"] for row in rows], dtype=float)
    gross = np.asarray([row["gross_return"] for row in rows], dtype=float)
    durations = np.asarray([row["duration_candles"] for row in rows], dtype=float)
    if not net.size:
        return {
            "sample_size": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "gross_profit_factor": 0.0,
            "expectancy": 0.0,
            "net_return": 0.0,
            "max_drawdown": 0.0,
            "recovery_factor": 0.0,
            "average_duration_candles": 0.0,
            "ict_score": 0.0,
            "ict_grade": "E",
            "ict_status": "REJEITADA",
            "minimum_filters_passed": False,
        }

    wins = net[net > 0]
    losses = net[net < 0]
    gross_wins = gross[gross > 0]
    gross_losses = gross[gross < 0]
    loss_total = abs(float(losses.sum()))
    gross_loss_total = abs(float(gross_losses.sum()))
    profit_factor = (
        float(wins.sum()) / loss_total
        if loss_total > 0
        else float("inf") if wins.size else 0.0
    )
    gross_profit_factor = (
        float(gross_wins.sum()) / gross_loss_total
        if gross_loss_total > 0
        else float("inf") if gross_wins.size else 0.0
    )
    equity = np.cumsum(net)
    peaks = np.maximum.accumulate(np.concatenate((np.array([0.0]), equity)))
    max_drawdown = float(np.max(peaks[1:] - equity))
    total_return = float(net.sum())
    recovery_factor = (
        max(total_return, 0.0) / max_drawdown
        if max_drawdown > 0
        else 5.0 if total_return > 0 else 0.0
    )
    certification = TraderIACertificationEngine().certify(
        TraderIACertificationInput(
            win_rate=float((net > 0).mean()),
            profit_factor=profit_factor,
            expectancy=float(net.mean()),
            max_drawdown=max_drawdown,
            sample_size=int(net.size),
            recovery_factor=recovery_factor,
        )
    )
    return {
        "sample_size": int(net.size),
        "win_rate": float((net > 0).mean()),
        "profit_factor": profit_factor,
        "gross_profit_factor": gross_profit_factor,
        "expectancy": float(net.mean()),
        "net_return": total_return,
        "max_drawdown": max_drawdown,
        "recovery_factor": recovery_factor,
        "average_duration_candles": float(durations.mean()),
        "ict_score": certification.ict_score,
        "ict_grade": certification.grade,
        "ict_status": certification.status,
        "minimum_filters_passed": certification.minimum_filters_passed,
        "ict_rejection_reasons": list(certification.rejection_reasons),
        "ict_components": certification.component_scores,
    }


def _evaluate_signal(
    market: MarketArrays,
    signal: np.ndarray,
    candidate: dict[str, Any],
    bounds: tuple[int, int],
    cost_fraction: float,
) -> dict[str, Any]:
    return summarize_outcomes(
        replay_segment(
            market,
            signal,
            bounds,
            stop_factor=float(candidate["stop_factor"]),
            risk_reward=float(candidate["risk_reward"]),
            round_trip_cost_fraction=cost_fraction,
        )
    )


def _candidate_key(candidate: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((name, str(value)) for name, value in candidate.items()))


def generate_candidates(count: int, seed: int) -> list[dict[str, Any]]:
    randomizer = random.Random(seed)
    candidates: list[dict[str, Any]] = []
    families = (
        "TREND_PULLBACK_CONTINUATION",
        "MOMENTUM_ACCELERATION",
        "BREAKOUT_EXPANSION",
        "SQUEEZE_RELEASE",
        "MEAN_REVERSION_REJECTION",
        "LIQUIDITY_RECLAIM",
        "STRUCTURE_CONTINUATION",
    )
    fast_slow = (
        (8, 34),
        (13, 34),
        (13, 55),
        (21, 55),
        (21, 89),
        (34, 89),
        (34, 144),
        (55, 144),
        (55, 200),
    )
    for _ in range(max(int(count), 1)):
        family = randomizer.choice(families)
        fast, slow = randomizer.choice(fast_slow)
        candidate: dict[str, Any] = {
            "family": family,
            "fast": fast,
            "slow": slow,
            "adx_min": randomizer.choice((0, 12, 15, 18, 20, 22, 25, 28)),
            "adx_rising": randomizer.choice((False, True)),
            "volume_min": randomizer.choice((0.0, 0.8, 1.0, 1.1, 1.2)),
            "stop_factor": randomizer.choice((0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5)),
            "risk_reward": randomizer.choice((1.0, 1.25, 1.5, 2.0, 2.5, 3.0)),
            "session": randomizer.choice(("ALL", "LONDON", "NEW_YORK", "ACTIVE", "OVERLAP", "ASIA")),
            "weekdays": randomizer.choice(("ALL", "MON_THU", "TUE_THU", "NOT_MONDAY")),
            "atr_regime": randomizer.choice(("ALL", "QUIET", "NORMAL", "EXPANDING")),
            "efficiency_period": randomizer.choice((10, 20, 30)),
            "efficiency_min": randomizer.choice((0.0, 0.10, 0.20, 0.30, 0.40)),
            "efficiency_max": 1.0,
            "slope_aligned": randomizer.choice((False, True)),
        }
        if family == "TREND_PULLBACK_CONTINUATION":
            candidate.update(
                touch_atr=randomizer.choice((0.10, 0.20, 0.35, 0.50)),
                wick_min=randomizer.choice((0.10, 0.20, 0.30, 0.40)),
                rsi_period=randomizer.choice((7, 14, 21)),
                rsi_low=randomizer.choice((30, 35, 40, 45)),
                rsi_high=randomizer.choice((55, 60, 65, 70)),
                roc_period=randomizer.choice((1, 3, 6, 12)),
            )
        elif family == "MOMENTUM_ACCELERATION":
            candidate.update(
                body_atr=randomizer.choice((0.30, 0.50, 0.70, 0.90, 1.10)),
                hist_min=randomizer.choice((0.0, 0.02, 0.05, 0.10)),
                roc_period=randomizer.choice((1, 3, 6, 12)),
                roc_min=randomizer.choice((0.0, 0.0002, 0.0005, 0.0010)),
                close_extreme=randomizer.choice((0.55, 0.65, 0.75, 0.85)),
            )
        elif family == "BREAKOUT_EXPANSION":
            candidate.update(
                lookback=randomizer.choice((10, 20, 40, 60)),
                range_atr=randomizer.choice((0.70, 0.90, 1.10, 1.30, 1.50)),
                close_extreme=randomizer.choice((0.55, 0.65, 0.75, 0.85)),
                trend_required=randomizer.choice((False, True)),
            )
        elif family == "SQUEEZE_RELEASE":
            candidate.update(
                lookback=randomizer.choice((10, 20, 40, 60)),
                squeeze_max=randomizer.choice((0.65, 0.75, 0.85, 0.95)),
                range_atr=randomizer.choice((0.80, 1.00, 1.20, 1.40)),
                trend_required=randomizer.choice((False, True)),
            )
        elif family == "MEAN_REVERSION_REJECTION":
            candidate.update(
                rsi_period=randomizer.choice((7, 14, 21)),
                rsi_extreme=randomizer.choice((20, 25, 30, 35, 40)),
                zscore_min=randomizer.choice((1.0, 1.25, 1.5, 1.75, 2.0, 2.5)),
                wick_min=randomizer.choice((0.10, 0.20, 0.30, 0.40)),
                adx_max=randomizer.choice((18, 20, 22, 25, 30, 35)),
                efficiency_max=randomizer.choice((0.20, 0.30, 0.40, 0.50)),
            )
        elif family == "LIQUIDITY_RECLAIM":
            candidate.update(
                lookback=randomizer.choice((10, 20, 40, 60)),
                wick_min=randomizer.choice((0.20, 0.30, 0.40, 0.50)),
                rsi_extreme=randomizer.choice((25, 30, 35, 40, 45)),
                adx_max=randomizer.choice((18, 20, 22, 25, 30, 35)),
            )
        else:
            candidate.update(
                lookback=randomizer.choice((10, 20, 40, 60)),
                reclaim_buffer_atr=randomizer.choice((0.05, 0.10, 0.20, 0.30)),
            )
        candidates.append(candidate)

    unique: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for candidate in candidates:
        key = _candidate_key(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _selection_score(
    development: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> float:
    block_pfs = [min(float(block["profit_factor"]), 3.0) for block in blocks]
    positive_blocks = sum(float(block["expectancy"]) > 0 for block in blocks)
    median_pf = float(np.median(block_pfs)) if block_pfs else 0.0
    minimum_pf = min(block_pfs) if block_pfs else 0.0
    return (
        min(float(development["ict_score"]), 100.0)
        + 20.0 * median_pf
        + 10.0 * minimum_pf
        + 5.0 * positive_blocks
        + min(int(development["sample_size"]), 400) / 20.0
        + min(float(development["recovery_factor"]), 5.0) * 2.0
    )


def _development_candidate_allowed(
    development: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> bool:
    if int(development["sample_size"]) < 80:
        return False
    if float(development["profit_factor"]) < 1.08:
        return False
    if float(development["expectancy"]) <= 0:
        return False
    if float(development["max_drawdown"]) > 0.20:
        return False
    populated = [block for block in blocks if int(block["sample_size"]) >= 8]
    if len(populated) < 3:
        return False
    if sum(float(block["expectancy"]) > 0 for block in populated) < 3:
        return False
    if min(float(block["profit_factor"]) for block in populated) < 0.75:
        return False
    return True


def _qualification(
    development: dict[str, Any],
    holdout: dict[str, Any],
    full: dict[str, Any],
    stress_holdout: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(full["sample_size"]) < 120:
        reasons.append("Amostra total abaixo de 120 trades.")
    if int(holdout["sample_size"]) < 20:
        reasons.append("Holdout abaixo de 20 trades.")
    if float(development["profit_factor"]) < 1.20:
        reasons.append("PF de desenvolvimento abaixo de 1.20.")
    if float(holdout["profit_factor"]) < 1.15:
        reasons.append("PF do holdout abaixo de 1.15.")
    if float(full["profit_factor"]) < 1.30:
        reasons.append("PF total liquido abaixo de 1.30.")
    if float(stress_holdout["profit_factor"]) < 1.05:
        reasons.append("PF do holdout sob custo estressado abaixo de 1.05.")
    if float(full["max_drawdown"]) > 0.15:
        reasons.append("Drawdown total acima de 15%.")
    populated = [block for block in blocks if int(block["sample_size"]) >= 8]
    if sum(float(block["expectancy"]) > 0 for block in populated) < 3:
        reasons.append("Menos de tres blocos temporais positivos.")
    if float(full["ict_score"]) < 70.0:
        reasons.append("ICT total abaixo de B (70).")
    if not bool(full["minimum_filters_passed"]):
        reasons.append("Filtros minimos do ICT nao atendidos.")
    return not reasons, reasons


def search_pair(
    pair: str,
    market: MarketArrays,
    candidates: list[dict[str, Any]],
    windows: ResearchWindows,
    *,
    cost_fraction: float,
    stress_cost_fraction: float,
) -> dict[str, Any]:
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        signal = build_signal(market, candidate)
        development = _evaluate_signal(
            market,
            signal,
            candidate,
            windows.development,
            cost_fraction,
        )
        if (
            int(development["sample_size"]) < 80
            or float(development["profit_factor"]) < 1.08
            or float(development["expectancy"]) <= 0
        ):
            continue
        blocks = [
            _evaluate_signal(market, signal, candidate, bounds, cost_fraction)
            for bounds in windows.stability_blocks
        ]
        if not _development_candidate_allowed(development, blocks):
            continue
        ranked.append(
            {
                "selection_score": _selection_score(development, blocks),
                "parameters": candidate,
                "development": development,
                "stability_blocks": blocks,
            }
        )
    ranked.sort(key=lambda row: float(row["selection_score"]), reverse=True)
    frozen = ranked[0] if ranked else None
    if frozen is None:
        return {
            "pair": pair,
            "alpha_id": f"{ALPHA_ID}_{pair}",
            "qualified": False,
            "status": "NO_DEVELOPMENT_SURVIVOR",
            "candidate_count": len(candidates),
            "development_survivors": 0,
            "winner": None,
        }

    candidate = frozen["parameters"]
    signal = build_signal(market, candidate)
    holdout = _evaluate_signal(
        market,
        signal,
        candidate,
        windows.holdout,
        cost_fraction,
    )
    full = _evaluate_signal(
        market,
        signal,
        candidate,
        (0, len(market.close)),
        cost_fraction,
    )
    stress_holdout = _evaluate_signal(
        market,
        signal,
        candidate,
        windows.holdout,
        stress_cost_fraction,
    )
    stress_full = _evaluate_signal(
        market,
        signal,
        candidate,
        (0, len(market.close)),
        stress_cost_fraction,
    )
    qualified, reasons = _qualification(
        frozen["development"],
        holdout,
        full,
        stress_holdout,
        frozen["stability_blocks"],
    )
    return {
        "pair": pair,
        "alpha_id": f"{ALPHA_ID}_{pair}",
        "qualified": qualified,
        "status": "QUALIFIED_FOR_M3_REPLAY" if qualified else "RESEARCH_NOT_QUALIFIED",
        "candidate_count": len(candidates),
        "development_survivors": len(ranked),
        "holdout_opened_after_winner_frozen": True,
        "qualification_reasons": reasons,
        "winner": {
            **frozen,
            "holdout": holdout,
            "full_sample": full,
            "stress_holdout": stress_holdout,
            "stress_full_sample": stress_full,
        },
        "development_top_five_without_holdout": ranked[:5],
    }


def discover_individual_alphas(
    snapshot_path: Path,
    *,
    timeframe: str = TIMEFRAME,
    candidate_count: int = 6_000,
    seed: int = 20260722,
    pairs: Iterable[str] | None = None,
    round_trip_cost_bps: float = DEFAULT_ROUND_TRIP_COST_BPS,
    stress_round_trip_cost_bps: float = STRESS_ROUND_TRIP_COST_BPS,
) -> dict[str, Any]:
    markets = {
        pair: enrich_market(market)
        for pair, market in load_markets_for_timeframe(
            snapshot_path,
            timeframe,
        ).items()
    }
    requested_pairs = {
        str(pair).strip().upper() for pair in (pairs or markets) if str(pair).strip()
    }
    selected = {
        pair: market
        for pair, market in sorted(markets.items())
        if pair in requested_pairs
    }
    if not selected:
        raise RuntimeError("No requested pairs were found in the snapshot.")
    candle_count = min(len(market.close) for market in selected.values())
    windows = chronological_research_windows(candle_count)
    cost_fraction = float(round_trip_cost_bps) / 10_000.0
    stress_cost_fraction = float(stress_round_trip_cost_bps) / 10_000.0
    results: dict[str, dict[str, Any]] = {}
    for pair, market in selected.items():
        pair_seed = seed + sum((index + 1) * ord(char) for index, char in enumerate(pair))
        candidates = generate_candidates(candidate_count, pair_seed)
        results[pair] = search_pair(
            pair,
            market,
            candidates,
            windows,
            cost_fraction=cost_fraction,
            stress_cost_fraction=stress_cost_fraction,
        )
        winner = results[pair].get("winner") or {}
        full = winner.get("full_sample") or {}
        holdout = winner.get("holdout") or {}
        print(
            json.dumps(
                {
                    "pair": pair,
                    "qualified": results[pair]["qualified"],
                    "survivors": results[pair]["development_survivors"],
                    "family": (winner.get("parameters") or {}).get("family"),
                    "full_pf": full.get("profit_factor"),
                    "holdout_pf": holdout.get("profit_factor"),
                    "ict": full.get("ict_score"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    qualified_pairs = [
        pair for pair, result in results.items() if bool(result["qualified"])
    ]
    return {
        "schema_version": "2.0",
        "alpha_id": ALPHA_ID,
        "status": "M3_RESEARCH_COMPLETE",
        "operational": False,
        "model_destination": MODEL_DESTINATION,
        "timeframe": str(timeframe).strip().upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(snapshot_path),
        "markets": list(selected),
        "candles_per_market": candle_count,
        "candidate_count_per_pair": candidate_count,
        "random_seed": seed,
        "round_trip_cost_bps": float(round_trip_cost_bps),
        "stress_round_trip_cost_bps": float(stress_round_trip_cost_bps),
        "windows": {
            "development": list(windows.development),
            "stability_blocks": [list(bounds) for bounds in windows.stability_blocks],
            "holdout": list(windows.holdout),
        },
        "selection_contract": (
            "One winner per pair is frozen on development and four chronological "
            "blocks before the final holdout is opened."
        ),
        "qualification_contract": {
            "minimum_total_trades": 120,
            "minimum_holdout_trades": 20,
            "minimum_development_pf": 1.20,
            "minimum_holdout_pf": 1.15,
            "minimum_total_pf": 1.30,
            "minimum_stress_holdout_pf": 1.05,
            "maximum_drawdown": 0.15,
            "minimum_positive_stability_blocks": 3,
            "minimum_ict": 70.0,
        },
        "qualified_pairs": qualified_pairs,
        "results": results,
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path(".traderia/research/alpha_sugerida_h1_20000_snapshot.json"),
    )
    parser.add_argument("--candidates", type=int, default=6_000)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--timeframe", default=TIMEFRAME)
    parser.add_argument("--pairs", nargs="*")
    parser.add_argument("--round-trip-cost-bps", type=float, default=DEFAULT_ROUND_TRIP_COST_BPS)
    parser.add_argument("--stress-round-trip-cost-bps", type=float, default=STRESS_ROUND_TRIP_COST_BPS)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".traderia/research/m3_alpha_sugerida_2_plus_individual_h1_20000.json"),
    )
    args = parser.parse_args()
    result = discover_individual_alphas(
        args.snapshot,
        timeframe=args.timeframe,
        candidate_count=args.candidates,
        seed=args.seed,
        pairs=args.pairs,
        round_trip_cost_bps=args.round_trip_cost_bps,
        stress_round_trip_cost_bps=args.stress_round_trip_cost_bps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "model_destination": result["model_destination"],
                "qualified_pairs": result["qualified_pairs"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
