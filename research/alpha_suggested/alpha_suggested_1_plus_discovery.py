"""Discover an explainable Alpha candidate without changing the operational Lab.

The experiment uses the local read-only MT5 history snapshot, freezes candidate
selection on chronological train/validation windows and opens the holdout only
after ranking. Results are written below ``.traderia/research`` and therefore do
not become an operational Alpha merely because this script was executed.
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

from research.traderia_certification_index import TraderIACertificationEngine


ALPHA_ID = "ALPHA_SUGERIDA_001_PLUS"
ALPHA_LABEL = "Alpha Sugerida 1+"
TIMEFRAME = "H1"
TRAIN_RANGE = (0, 3000)
VALIDATION_RANGE = (3000, 4000)
HOLDOUT_RANGE = (4000, 5000)
MINIMUM_DISTANCE_PERCENT = 0.0005


@dataclass(frozen=True)
class MarketArrays:
    pair: str
    frame: pd.DataFrame
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    atr: np.ndarray


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def engineer_features(pair: str, candles: list[dict[str, Any]]) -> MarketArrays:
    frame = pd.DataFrame(candles).rename(
        columns={
            "abertura": "open",
            "maxima": "high",
            "minima": "low",
            "fechamento": "close",
        }
    )
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = _numeric(frame[column])

    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        (
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)
    frame["atr14"] = true_range.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()
    frame["atr50"] = true_range.ewm(
        alpha=1 / 50,
        adjust=False,
        min_periods=50,
    ).mean()
    for period in (10, 20, 30, 50, 100):
        frame[f"ema{period}"] = frame["close"].ewm(
            span=period,
            adjust=False,
            min_periods=period,
        ).mean()

    delta = frame["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    frame["rsi"] = 100 - (100 / (1 + relative_strength))

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
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()
    plus_di = 100 * plus_dm.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean() / smoothed_range
    minus_di = 100 * minus_dm.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean() / smoothed_range
    directional_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / directional_sum
    frame["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    frame["adx_delta"] = frame["adx"] - frame["adx"].shift(3)

    candle_range = (frame["high"] - frame["low"]).replace(0, np.nan)
    frame["body_atr"] = (frame["close"] - frame["open"]).abs() / frame["atr14"]
    frame["range_atr"] = candle_range / frame["atr14"]
    frame["close_position"] = (frame["close"] - frame["low"]) / candle_range
    frame["upper_wick"] = (
        frame["high"] - frame[["open", "close"]].max(axis=1)
    ) / candle_range
    frame["lower_wick"] = (
        frame[["open", "close"]].min(axis=1) - frame["low"]
    ) / candle_range
    frame["volume_ratio"] = frame["volume"] / frame["volume"].rolling(
        20,
        min_periods=20,
    ).mean()
    frame["atr_ratio"] = frame["atr14"] / frame["atr50"]
    frame["momentum_3"] = frame["close"] / frame["close"].shift(3) - 1
    frame["momentum_5"] = frame["close"] / frame["close"].shift(5) - 1
    timestamp = pd.to_datetime(frame["data"], utc=True, errors="coerce")
    frame["hour_utc"] = timestamp.dt.hour
    frame["weekday"] = timestamp.dt.weekday
    frame["efficiency_20"] = (
        (frame["close"] - frame["close"].shift(20)).abs()
        / frame["close"].diff().abs().rolling(20, min_periods=20).sum().replace(0, np.nan)
    )
    frame["ema50_slope_atr"] = (
        frame["ema50"] - frame["ema50"].shift(5)
    ) / frame["atr14"]
    for period in (10, 20, 40):
        frame[f"prior_high_{period}"] = frame["high"].shift(1).rolling(
            period,
            min_periods=period,
        ).max()
        frame[f"prior_low_{period}"] = frame["low"].shift(1).rolling(
            period,
            min_periods=period,
        ).min()

    return MarketArrays(
        pair=pair,
        frame=frame,
        high=frame["high"].to_numpy(dtype=float),
        low=frame["low"].to_numpy(dtype=float),
        close=frame["close"].to_numpy(dtype=float),
        atr=frame["atr14"].to_numpy(dtype=float),
    )


def load_markets(snapshot_path: Path) -> dict[str, MarketArrays]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    markets: dict[str, MarketArrays] = {}
    for key, candles in payload.get("candles_by_market", {}).items():
        pair, timeframe = str(key).split("|", maxsplit=1)
        if timeframe.upper() != TIMEFRAME:
            continue
        markets[pair.upper()] = engineer_features(pair.upper(), list(candles))
    if not markets:
        raise RuntimeError(f"No {TIMEFRAME} markets found in {snapshot_path}.")
    return markets


def _as_bool(series: pd.Series) -> np.ndarray:
    return series.fillna(False).to_numpy(dtype=bool)


def build_signal(market: MarketArrays, candidate: dict[str, Any]) -> np.ndarray:
    frame = market.frame
    family = str(candidate["family"])
    fast = frame[f"ema{candidate['fast']}"]
    slow = frame[f"ema{candidate['slow']}"]
    trend_buy = fast > slow
    trend_sell = fast < slow
    adx_ok = frame["adx"] >= float(candidate["adx_min"])
    if bool(candidate["adx_rising"]):
        adx_ok &= frame["adx_delta"] > 0
    volume_ok = frame["volume_ratio"] >= float(candidate["volume_min"])

    if family == "COMPRESSION_RELEASE":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        base = (
            (frame["atr_ratio"].shift(1) <= float(candidate["compression"]))
            & (frame["range_atr"] >= float(candidate["expansion"]))
            & adx_ok
            & volume_ok
        )
        extreme = float(candidate["close_extreme"])
        buy = base & (frame["close"] > prior_high) & (frame["close_position"] >= extreme)
        sell = base & (frame["close"] < prior_low) & (frame["close_position"] <= 1 - extreme)
        if bool(candidate["trend_required"]):
            buy &= trend_buy
            sell &= trend_sell
    elif family == "TREND_IMPULSE":
        base = (
            (frame["body_atr"] >= float(candidate["body_atr"]))
            & adx_ok
            & volume_ok
        )
        extreme = float(candidate["close_extreme"])
        momentum = frame[str(candidate["momentum"])]
        buy = (
            base
            & trend_buy
            & (frame["close"] > frame["open"])
            & (frame["close_position"] >= extreme)
            & (momentum > 0)
        )
        sell = (
            base
            & trend_sell
            & (frame["close"] < frame["open"])
            & (frame["close_position"] <= 1 - extreme)
            & (momentum < 0)
        )
    elif family == "PULLBACK_REJECTION":
        tolerance = float(candidate["touch_tolerance"])
        touched_buy = (frame["low"] <= fast * (1 + tolerance)) & (frame["close"] > fast)
        touched_sell = (frame["high"] >= fast * (1 - tolerance)) & (frame["close"] < fast)
        base = (
            adx_ok
            & volume_ok
            & (frame["body_atr"] >= float(candidate["body_atr"]))
        )
        rsi_low = float(candidate["rsi_buy_low"])
        rsi_high = float(candidate["rsi_buy_high"])
        buy = (
            base
            & trend_buy
            & touched_buy
            & (frame["close"] > frame["open"])
            & (frame["lower_wick"] >= float(candidate["wick_min"]))
            & frame["rsi"].between(rsi_low, rsi_high)
        )
        sell = (
            base
            & trend_sell
            & touched_sell
            & (frame["close"] < frame["open"])
            & (frame["upper_wick"] >= float(candidate["wick_min"]))
            & frame["rsi"].between(100 - rsi_high, 100 - rsi_low)
        )
    elif family == "LIQUIDITY_SWEEP_RECLAIM":
        lookback = int(candidate["lookback"])
        prior_high = frame[f"prior_high_{lookback}"]
        prior_low = frame[f"prior_low_{lookback}"]
        base = volume_ok & (frame["range_atr"] >= float(candidate["expansion"]))
        rsi_extreme = float(candidate["rsi_extreme"])
        buy = (
            base
            & (frame["low"] < prior_low)
            & (frame["close"] > prior_low)
            & (frame["lower_wick"] >= float(candidate["wick_min"]))
            & (frame["rsi"] <= rsi_extreme)
        )
        sell = (
            base
            & (frame["high"] > prior_high)
            & (frame["close"] < prior_high)
            & (frame["upper_wick"] >= float(candidate["wick_min"]))
            & (frame["rsi"] >= 100 - rsi_extreme)
        )
        if bool(candidate["trend_required"]):
            buy &= trend_buy
            sell &= trend_sell
        if float(candidate["adx_max"]) > 0:
            buy &= frame["adx"] <= float(candidate["adx_max"])
            sell &= frame["adx"] <= float(candidate["adx_max"])
    else:
        raise ValueError(f"Unknown candidate family: {family}")

    signal = np.zeros(len(frame), dtype=np.int8)
    signal[_as_bool(buy)] = 1
    signal[_as_bool(sell)] = -1
    signal = _apply_context_filters(signal, frame, candidate)
    previous = np.concatenate((np.array([0], dtype=np.int8), signal[:-1]))
    signal[(signal != 0) & (signal == previous)] = 0
    return signal


def _apply_context_filters(
    signal: np.ndarray,
    frame: pd.DataFrame,
    candidate: dict[str, Any],
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

    weekday_filter = str(candidate.get("weekdays", "ALL"))
    if weekday_filter == "MON_THU":
        mask &= weekdays <= 3
    elif weekday_filter == "TUE_THU":
        mask &= (weekdays >= 1) & (weekdays <= 3)
    elif weekday_filter == "NOT_MONDAY":
        mask &= weekdays >= 1

    efficiency = frame["efficiency_20"].to_numpy(dtype=float)
    mask &= np.nan_to_num(efficiency, nan=-1.0) >= float(
        candidate.get("efficiency_min", 0.0)
    )
    atr_ratio = frame["atr_ratio"].to_numpy(dtype=float)
    atr_regime = str(candidate.get("atr_regime", "ALL"))
    if atr_regime == "QUIET":
        mask &= atr_ratio <= 0.9
    elif atr_regime == "NORMAL":
        mask &= (atr_ratio > 0.9) & (atr_ratio < 1.1)
    elif atr_regime == "EXPANDING":
        mask &= atr_ratio >= 1.1

    if bool(candidate.get("slope_aligned", False)):
        slope = frame["ema50_slope_atr"].to_numpy(dtype=float)
        mask &= ((signal > 0) & (slope > 0)) | ((signal < 0) & (slope < 0))
    filtered = signal.copy()
    filtered[~mask] = 0
    return filtered


def replay_segment(
    market: MarketArrays,
    signal: np.ndarray,
    start: int,
    end: int,
    *,
    stop_factor: float,
    risk_reward: float,
) -> list[float]:
    returns: list[float] = []
    index = max(int(start), 100)
    end = min(int(end), len(market.close))
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
        returns.append(-risk_fraction if stop_first else risk_fraction * risk_reward)
        index = index + 2 + exit_offset
    return returns


def summarize_returns(values: Iterable[float]) -> dict[str, Any]:
    returns = np.asarray(list(values), dtype=float)
    if not returns.size:
        return {
            "sample_size": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "ict_score": 0.0,
            "ict_grade": "E",
            "minimum_filters_passed": False,
        }
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    gross_loss = abs(float(losses.sum()))
    profit_factor = (
        float(wins.sum()) / gross_loss
        if gross_loss > 0
        else float("inf") if wins.size else 0.0
    )
    equity = np.cumsum(returns)
    peaks = np.maximum.accumulate(np.concatenate((np.array([0.0]), equity)))
    max_drawdown = float(np.max(peaks[1:] - equity))
    win_rate = float((returns > 0).mean())
    expectancy = float(returns.mean())
    certification = TraderIACertificationEngine().from_research_metrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_return=expectancy,
        max_drawdown=max_drawdown,
        sample_size=int(returns.size),
    )
    return {
        "sample_size": int(returns.size),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_drawdown": max_drawdown,
        "ict_score": certification.ict_score,
        "ict_grade": certification.grade,
        "minimum_filters_passed": certification.minimum_filters_passed,
        "ict_components": certification.component_scores,
    }


def evaluate_candidate(
    markets: dict[str, MarketArrays],
    candidate: dict[str, Any],
    bounds: tuple[int, int],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    all_returns: list[float] = []
    by_pair: dict[str, dict[str, Any]] = {}
    for pair, market in sorted(markets.items()):
        signal = build_signal(market, candidate)
        returns = replay_segment(
            market,
            signal,
            *bounds,
            stop_factor=float(candidate["stop_factor"]),
            risk_reward=float(candidate["risk_reward"]),
        )
        all_returns.extend(returns)
        by_pair[pair] = summarize_returns(returns)
    return summarize_returns(all_returns), by_pair


def generate_candidates(count: int, seed: int) -> list[dict[str, Any]]:
    randomizer = random.Random(seed)
    candidates: list[dict[str, Any]] = []
    for _ in range(max(count, 1)):
        family = randomizer.choice(
            (
                "COMPRESSION_RELEASE",
                "TREND_IMPULSE",
                "PULLBACK_REJECTION",
                "LIQUIDITY_SWEEP_RECLAIM",
            )
        )
        candidate: dict[str, Any] = {
            "family": family,
            "fast": randomizer.choice((10, 20, 30)),
            "slow": randomizer.choice((50, 100)),
            "adx_min": randomizer.choice((0, 15, 18, 20, 22, 25)),
            "adx_rising": randomizer.choice((False, True)),
            "volume_min": randomizer.choice((0.0, 0.8, 1.0, 1.1)),
            "stop_factor": randomizer.choice((1.0, 1.5, 2.0, 2.5)),
            "risk_reward": randomizer.choice((1.0, 1.5, 2.0, 2.5, 3.0)),
        }
        if family == "COMPRESSION_RELEASE":
            candidate.update(
                lookback=randomizer.choice((10, 20, 40)),
                compression=randomizer.choice((0.70, 0.80, 0.90, 1.0)),
                expansion=randomizer.choice((0.8, 1.0, 1.2)),
                close_extreme=randomizer.choice((0.60, 0.70, 0.80)),
                trend_required=randomizer.choice((False, True)),
            )
        elif family == "TREND_IMPULSE":
            candidate.update(
                body_atr=randomizer.choice((0.4, 0.6, 0.8, 1.0)),
                close_extreme=randomizer.choice((0.60, 0.70, 0.80)),
                momentum=randomizer.choice(("momentum_3", "momentum_5")),
            )
        elif family == "PULLBACK_REJECTION":
            candidate.update(
                touch_tolerance=randomizer.choice((0.0001, 0.0003, 0.0005)),
                body_atr=randomizer.choice((0.15, 0.30, 0.50)),
                wick_min=randomizer.choice((0.15, 0.25, 0.35)),
                rsi_buy_low=randomizer.choice((30, 35, 40)),
                rsi_buy_high=randomizer.choice((55, 60, 65)),
            )
        else:
            candidate.update(
                lookback=randomizer.choice((10, 20, 40)),
                expansion=randomizer.choice((0.6, 0.8, 1.0)),
                wick_min=randomizer.choice((0.25, 0.35, 0.45)),
                rsi_extreme=randomizer.choice((35, 40, 45)),
                trend_required=randomizer.choice((False, True)),
                adx_max=randomizer.choice((0, 20, 25, 30)),
            )
        candidate.update(
            session=randomizer.choice(
                ("ALL", "LONDON", "NEW_YORK", "ACTIVE", "OVERLAP", "ASIA")
            ),
            weekdays=randomizer.choice(
                ("ALL", "MON_THU", "TUE_THU", "NOT_MONDAY")
            ),
            efficiency_min=randomizer.choice((0.0, 0.15, 0.25, 0.35)),
            atr_regime=randomizer.choice(
                ("ALL", "QUIET", "NORMAL", "EXPANDING")
            ),
            slope_aligned=randomizer.choice((False, True)),
        )
        candidates.append(candidate)

    unique: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for candidate in candidates:
        key = tuple(sorted((name, str(value)) for name, value in candidate.items()))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _selection_score(train: dict[str, Any], validation: dict[str, Any]) -> float:
    return (
        min(float(train["ict_score"]), float(validation["ict_score"]))
        + 2 * min(float(train["profit_factor"]), float(validation["profit_factor"]))
        + min(int(train["sample_size"]), 300) / 300
    )


def chronological_windows(candle_count: int) -> dict[str, tuple[int, int]]:
    """Freeze a 60/20/20 split before candidate ranking."""
    safe_count = max(int(candle_count), 0)
    train_end = int(safe_count * 0.60)
    validation_end = int(safe_count * 0.80)
    return {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "holdout": (validation_end, safe_count),
    }


def discover(
    snapshot_path: Path,
    *,
    candidate_count: int = 320,
    seed: int = 20260721,
    finalist_count: int = 5,
) -> dict[str, Any]:
    markets = load_markets(snapshot_path)
    candle_count = min(len(market.close) for market in markets.values())
    windows = chronological_windows(candle_count)
    candidates = generate_candidates(candidate_count, seed)
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        train, _ = evaluate_candidate(markets, candidate, windows["train"])
        if (
            int(train["sample_size"]) < 100
            or float(train["profit_factor"]) < 1.15
            or float(train["expectancy"]) <= 0
        ):
            continue
        validation, _ = evaluate_candidate(
            markets,
            candidate,
            windows["validation"],
        )
        if (
            int(validation["sample_size"]) < 35
            or float(validation["profit_factor"]) < 1.05
            or float(validation["expectancy"]) <= 0
        ):
            continue
        ranked.append(
            {
                "selection_score": _selection_score(train, validation),
                "parameters": candidate,
                "train": train,
                "validation": validation,
            }
        )
    ranked.sort(key=lambda row: float(row["selection_score"]), reverse=True)

    finalists: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked[: max(finalist_count, 1)], start=1):
        holdout, holdout_by_pair = evaluate_candidate(
            markets,
            row["parameters"],
            windows["holdout"],
        )
        full, full_by_pair = evaluate_candidate(
            markets,
            row["parameters"],
            (0, candle_count),
        )
        finalists.append(
            {
                **row,
                "frozen_rank": rank,
                "holdout": holdout,
                "holdout_by_pair": holdout_by_pair,
                "full_sample": full,
                "full_sample_by_pair": full_by_pair,
            }
        )

    winner = finalists[0] if finalists else None
    qualified = bool(
        winner
        and winner["holdout"]["minimum_filters_passed"]
        and float(winner["holdout"]["ict_score"]) >= 80.0
    )
    return {
        "schema_version": "1.0",
        "alpha_id": ALPHA_ID,
        "alpha_label": ALPHA_LABEL,
        "status": "QUALIFIED_A_OR_BETTER" if qualified else "RESEARCH_NOT_QUALIFIED",
        "operational": False,
        "model_destination_after_approval": "MODELO_2",
        "timeframe": TIMEFRAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(snapshot_path),
        "markets": sorted(markets),
        "candles_per_market": candle_count,
        "chronological_windows": {
            name: list(bounds) for name, bounds in windows.items()
        },
        "random_seed": seed,
        "candidate_count_requested": candidate_count,
        "candidate_count_unique": len(candidates),
        "candidate_count_surviving_train_validation": len(ranked),
        "holdout_opened_only_after_frozen_ranking": True,
        "qualification_rule": "Holdout ICT >= 80 and all current minimum ICT filters passed.",
        "winner": winner,
        "finalists": finalists,
        "limitations": [
            "ICT is calculated globally across the eight H1 pairs in this experiment.",
            "The replay is gross and does not yet subtract spread, commission or slippage.",
            "A qualified result still requires cost stress, walk-forward and Demo forward validation.",
            "The current ICT recovery component uses average return divided by total drawdown.",
        ],
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path(".traderia/mt5_research_history_snapshot.json"),
    )
    parser.add_argument("--candidates", type=int, default=320)
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            ".traderia/research/alpha_sugerida_1_plus_discovery.json"
        ),
    )
    args = parser.parse_args()
    result = discover(
        args.snapshot,
        candidate_count=args.candidates,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    winner = result.get("winner") or {}
    print(json.dumps({
        "status": result["status"],
        "candidate_count_unique": result["candidate_count_unique"],
        "survivors": result["candidate_count_surviving_train_validation"],
        "winner_parameters": winner.get("parameters"),
        "train": winner.get("train"),
        "validation": winner.get("validation"),
        "holdout": winner.get("holdout"),
        "full_sample": winner.get("full_sample"),
        "output": str(args.output),
    }, indent=2, ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
