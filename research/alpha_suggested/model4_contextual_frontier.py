"""Research a causal, contextual frontier for a future Model 4 candidate.

The operational M4 already mirrors M1. This experiment therefore writes only
to ``MODELO_4_PESQUISA`` and never enters the runtime index. It reuses the five
development-only M30 candidates from the M3 study, then tests context that the
previous search did not model: completed H1/H4 trend, cross-pair currency
strength, BUY/SELL asymmetry, rolling volatility percentiles and next-bar-open
execution.
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

from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    DEFAULT_ROUND_TRIP_COST_BPS,
    MINIMUM_DISTANCE_PERCENT,
    STRESS_ROUND_TRIP_COST_BPS,
    _selection_score,
    build_signal,
    enrich_market,
    load_markets_for_timeframe,
    summarize_outcomes,
)


MODEL_DESTINATION = "MODELO_4_PESQUISA"
ALPHA_ID = "ALPHA_SUGERIDA_003_CONTEXTUAL_MTF"
PRIMARY_TIMEFRAME = "M30"
DEFAULT_M3_ARTIFACT = Path(
    ".traderia/research/m3_alpha_sugerida_2_plus_individual_m30_20000.json"
)
DEFAULT_M30_SNAPSHOT = Path(
    ".traderia/research/m3_alpha_sugerida_m30_20000_snapshot.json"
)
DEFAULT_H1_SNAPSHOT = Path(
    ".traderia/research/alpha_sugerida_h1_20000_snapshot.json"
)
DEFAULT_H4_SNAPSHOT = Path(
    ".traderia/research/m3_alpha_sugerida_h4_10000_snapshot.json"
)
DEFAULT_OUTPUT = Path(
    ".traderia/research/modelo_4_pesquisa_contextual_mtf.json"
)


@dataclass(frozen=True)
class FrontierWindows:
    discovery: tuple[int, int]
    stability_blocks: tuple[tuple[int, int], ...]
    validation: tuple[int, int]
    embargo: tuple[int, int]
    holdout: tuple[int, int]


@dataclass(frozen=True)
class ContextArrays:
    h1_trend: np.ndarray
    h1_adx: np.ndarray
    h4_trend: np.ndarray
    h4_adx: np.ndarray
    strength_fast: np.ndarray
    strength_slow: np.ndarray
    volatility_low: np.ndarray
    volatility_high: np.ndarray


def frontier_windows(candle_count: int) -> FrontierWindows:
    safe_count = max(int(candle_count), 0)
    discovery_end = int(safe_count * 0.60)
    validation_end = int(safe_count * 0.75)
    holdout_start = int(safe_count * 0.80)
    block_size = discovery_end // 4
    blocks = tuple(
        (
            index * block_size,
            discovery_end if index == 3 else (index + 1) * block_size,
        )
        for index in range(4)
    )
    return FrontierWindows(
        discovery=(0, discovery_end),
        stability_blocks=blocks,
        validation=(discovery_end, validation_end),
        embargo=(validation_end, holdout_start),
        holdout=(holdout_start, safe_count),
    )


def _timestamps(frame: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(frame["data"], utc=True, errors="coerce")


def _align_higher_timeframe(
    primary_frame: pd.DataFrame,
    higher_frame: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Align only the previous completed higher-timeframe candle."""
    trend = np.where(
        higher_frame["ema21"] > higher_frame["ema55"],
        1.0,
        np.where(higher_frame["ema21"] < higher_frame["ema55"], -1.0, 0.0),
    )
    higher = pd.DataFrame(
        {
            "timestamp": _timestamps(higher_frame),
            "trend": pd.Series(trend, index=higher_frame.index).shift(1),
            "adx": higher_frame["adx"].shift(1),
        }
    ).dropna(subset=["timestamp"])
    primary = pd.DataFrame({"timestamp": _timestamps(primary_frame)})
    merged = pd.merge_asof(
        primary.sort_values("timestamp"),
        higher.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    ).sort_index()
    return (
        merged["trend"].fillna(0.0).to_numpy(dtype=float),
        merged["adx"].fillna(0.0).to_numpy(dtype=float),
    )


def currency_strength_edges(
    markets: dict[str, Any],
    lookback: int,
) -> dict[str, np.ndarray]:
    """Build causal cross-pair base-minus-quote strength z-spreads."""
    returns: dict[str, pd.Series] = {}
    all_timestamps: set[pd.Timestamp] = set()
    for pair, market in markets.items():
        timestamp = _timestamps(market.frame)
        values = np.log(market.frame["close"]).diff(int(lookback))
        series = pd.Series(values.to_numpy(dtype=float), index=timestamp)
        series = series[~series.index.duplicated(keep="last")]
        returns[pair] = series
        all_timestamps.update(series.index.dropna())
    index = pd.DatetimeIndex(sorted(all_timestamps))
    currencies = sorted({pair[:3] for pair in markets} | {pair[3:] for pair in markets})
    sums = pd.DataFrame(0.0, index=index, columns=currencies)
    counts = pd.DataFrame(0.0, index=index, columns=currencies)
    for pair, series in returns.items():
        aligned = series.reindex(index)
        valid = aligned.notna().astype(float)
        base, quote = pair[:3], pair[3:]
        sums[base] = sums[base].add(aligned.fillna(0.0), fill_value=0.0)
        sums[quote] = sums[quote].sub(aligned.fillna(0.0), fill_value=0.0)
        counts[base] = counts[base].add(valid, fill_value=0.0)
        counts[quote] = counts[quote].add(valid, fill_value=0.0)
    strength = sums.divide(counts.replace(0.0, np.nan))
    row_mean = strength.mean(axis=1)
    row_std = strength.std(axis=1).replace(0.0, np.nan)
    zscore = strength.sub(row_mean, axis=0).divide(row_std, axis=0)
    edges: dict[str, np.ndarray] = {}
    for pair, market in markets.items():
        pair_index = pd.DatetimeIndex(_timestamps(market.frame))
        edge = (zscore[pair[:3]] - zscore[pair[3:]]).reindex(pair_index)
        edges[pair] = edge.fillna(0.0).to_numpy(dtype=float)
    return edges


def build_contexts(
    primary_markets: dict[str, Any],
    h1_markets: dict[str, Any],
    h4_markets: dict[str, Any],
) -> dict[str, ContextArrays]:
    fast_strength = currency_strength_edges(primary_markets, 3)
    slow_strength = currency_strength_edges(primary_markets, 12)
    contexts: dict[str, ContextArrays] = {}
    for pair, primary in primary_markets.items():
        h1_trend, h1_adx = _align_higher_timeframe(
            primary.frame,
            h1_markets[pair].frame,
        )
        h4_trend, h4_adx = _align_higher_timeframe(
            primary.frame,
            h4_markets[pair].frame,
        )
        ratio = primary.frame["atr_ratio"]
        low = ratio.rolling(500, min_periods=200).quantile(0.30).shift(1)
        high = ratio.rolling(500, min_periods=200).quantile(0.70).shift(1)
        contexts[pair] = ContextArrays(
            h1_trend=h1_trend,
            h1_adx=h1_adx,
            h4_trend=h4_trend,
            h4_adx=h4_adx,
            strength_fast=fast_strength[pair],
            strength_slow=slow_strength[pair],
            volatility_low=low.to_numpy(dtype=float),
            volatility_high=high.to_numpy(dtype=float),
        )
    return contexts


def load_base_candidates(
    artifact: dict[str, Any],
    pair: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    result = artifact.get("results", {}).get(pair, {})
    if not isinstance(result, dict):
        return []
    candidates = result.get("development_top_five_without_holdout", [])
    parameters = [
        dict(candidate.get("parameters", {}))
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("parameters"), dict)
    ]
    if not parameters:
        winner = result.get("winner", {})
        if isinstance(winner, dict) and isinstance(winner.get("parameters"), dict):
            parameters = [dict(winner["parameters"])]
    return parameters[: max(int(limit), 1)]


def generate_overlay_candidates(
    base_count: int,
    count: int,
    seed: int,
) -> list[dict[str, Any]]:
    randomizer = random.Random(seed)
    options: list[dict[str, Any]] = [
        {
            "base_index": 0,
            "direction_mode": "BOTH",
            "h1_mode": "NONE",
            "h4_mode": "NONE",
            "htf_adx_min": 0,
            "strength_mode": "NONE",
            "strength_min": 0.0,
            "volatility_band": "ALL",
        }
    ]
    direction_modes = ("BOTH", "BUY_ONLY", "SELL_ONLY")
    htf_modes = ("NONE", "NOT_OPPOSED", "ALIGNED")
    strength_modes = (
        "NONE",
        "CONFIRM_FAST",
        "CONFIRM_SLOW",
        "CONFIRM_BOTH",
        "FADE_FAST",
    )
    while len(options) < max(int(count), 1):
        strength_mode = randomizer.choice(strength_modes)
        option = {
            "base_index": randomizer.randrange(max(int(base_count), 1)),
            "direction_mode": randomizer.choice(direction_modes),
            "h1_mode": randomizer.choice(htf_modes),
            "h4_mode": randomizer.choice(htf_modes),
            "htf_adx_min": randomizer.choice((0, 15, 20, 25)),
            "strength_mode": strength_mode,
            "strength_min": (
                0.0
                if strength_mode == "NONE"
                else randomizer.choice((0.25, 0.50, 0.75, 1.00, 1.50))
            ),
            "volatility_band": randomizer.choice(("ALL", "LOW", "MID", "HIGH")),
        }
        options.append(option)
    unique: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for option in options:
        key = tuple(sorted((name, str(value)) for name, value in option.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(option)
    return unique


def apply_context_overlay(
    base_signal: np.ndarray,
    context: ContextArrays,
    atr_ratio: np.ndarray,
    overlay: dict[str, Any],
) -> np.ndarray:
    signal = np.asarray(base_signal, dtype=np.int8).copy()
    active = signal != 0
    direction_mode = str(overlay["direction_mode"])
    if direction_mode == "BUY_ONLY":
        active &= signal > 0
    elif direction_mode == "SELL_ONLY":
        active &= signal < 0

    adx_min = float(overlay["htf_adx_min"])
    for mode_name, trend, adx in (
        (str(overlay["h1_mode"]), context.h1_trend, context.h1_adx),
        (str(overlay["h4_mode"]), context.h4_trend, context.h4_adx),
    ):
        if mode_name == "NONE":
            continue
        strong = adx >= adx_min
        relation = trend * signal
        if mode_name == "ALIGNED":
            active &= strong & (relation > 0)
        else:
            active &= ~(strong & (relation < 0))

    strength_mode = str(overlay["strength_mode"])
    strength_min = float(overlay["strength_min"])
    fast_edge = context.strength_fast * signal
    slow_edge = context.strength_slow * signal
    if strength_mode == "CONFIRM_FAST":
        active &= fast_edge >= strength_min
    elif strength_mode == "CONFIRM_SLOW":
        active &= slow_edge >= strength_min
    elif strength_mode == "CONFIRM_BOTH":
        active &= (fast_edge >= strength_min) & (slow_edge >= strength_min)
    elif strength_mode == "FADE_FAST":
        active &= fast_edge <= -strength_min

    band = str(overlay["volatility_band"])
    if band == "LOW":
        active &= atr_ratio <= context.volatility_low
    elif band == "MID":
        active &= (atr_ratio > context.volatility_low) & (
            atr_ratio < context.volatility_high
        )
    elif band == "HIGH":
        active &= atr_ratio >= context.volatility_high
    signal[~active] = 0
    return signal


def precompute_next_open_paths(
    market: Any,
    signal: np.ndarray,
    *,
    stop_factor: float,
    risk_reward: float,
) -> list[dict[str, float]]:
    """Resolve each isolated signal using entry at the next candle open."""
    opens = market.frame["open"].to_numpy(dtype=float)
    paths: list[dict[str, float]] = []
    for signal_index in np.flatnonzero(signal):
        entry_index = int(signal_index) + 1
        if entry_index >= len(market.close):
            continue
        direction = int(signal[signal_index])
        atr = float(market.atr[signal_index])
        entry = float(opens[entry_index])
        if direction == 0 or not math.isfinite(atr) or entry <= 0:
            continue
        distance = max(atr * stop_factor, abs(entry) * MINIMUM_DISTANCE_PERCENT)
        stop = entry - direction * distance
        target = entry + direction * distance * risk_reward
        future_high = market.high[entry_index:]
        future_low = market.low[entry_index:]
        if direction > 0:
            stop_hits = np.flatnonzero(future_low <= stop)
            target_hits = np.flatnonzero(future_high >= target)
        else:
            stop_hits = np.flatnonzero(future_high >= stop)
            target_hits = np.flatnonzero(future_low <= target)
        first_stop = int(stop_hits[0]) if stop_hits.size else None
        first_target = int(target_hits[0]) if target_hits.size else None
        if first_stop is None and first_target is None:
            continue
        stop_first = first_stop is not None and (
            first_target is None or first_stop <= first_target
        )
        exit_offset = first_stop if stop_first else first_target
        if exit_offset is None:
            continue
        risk_fraction = distance / abs(entry)
        paths.append(
            {
                "signal_index": float(signal_index),
                "entry_index": float(entry_index),
                "exit_index": float(entry_index + exit_offset),
                "gross_return": (
                    -risk_fraction if stop_first else risk_fraction * risk_reward
                ),
                "duration_candles": float(exit_offset + 1),
            }
        )
    return paths


def replay_precomputed_paths(
    paths: Iterable[dict[str, float]],
    accepted_signal: np.ndarray,
    bounds: tuple[int, int],
    cost_fraction: float,
) -> list[dict[str, float]]:
    start, end = bounds
    next_available = max(int(start), 0)
    outcomes: list[dict[str, float]] = []
    for path in paths:
        signal_index = int(path["signal_index"])
        entry_index = int(path["entry_index"])
        exit_index = int(path["exit_index"])
        if signal_index < start or signal_index >= end:
            continue
        if entry_index < next_available or exit_index >= end:
            continue
        if not accepted_signal[signal_index]:
            continue
        outcomes.append(
            {
                "gross_return": float(path["gross_return"]),
                "net_return": float(path["gross_return"]) - cost_fraction,
                "duration_candles": float(path["duration_candles"]),
            }
        )
        next_available = exit_index + 1
    return outcomes


def _evaluate_paths(
    paths: Iterable[dict[str, float]],
    signal: np.ndarray,
    bounds: tuple[int, int],
    cost_fraction: float,
) -> dict[str, Any]:
    return summarize_outcomes(
        replay_precomputed_paths(paths, signal, bounds, cost_fraction)
    )


def _validation_score(
    discovery: dict[str, Any],
    validation: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> float:
    validation_pf = min(float(validation["profit_factor"]), 3.0)
    consistency_penalty = abs(
        min(float(discovery["profit_factor"]), 3.0) - validation_pf
    )
    return (
        _selection_score(discovery, blocks)
        + 25.0 * validation_pf
        + min(int(validation["sample_size"]), 100) / 5.0
        - 12.0 * consistency_penalty
    )


def _frontier_discovery_allowed(
    discovery: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> bool:
    """Use a discovery threshold compatible with the shorter 60% window."""
    if int(discovery["sample_size"]) < 45:
        return False
    if float(discovery["profit_factor"]) < 1.08:
        return False
    if float(discovery["expectancy"]) <= 0:
        return False
    if float(discovery["max_drawdown"]) > 0.20:
        return False
    populated = [block for block in blocks if int(block["sample_size"]) >= 5]
    if len(populated) < 3:
        return False
    if sum(float(block["expectancy"]) > 0 for block in populated) < 3:
        return False
    if min(float(block["profit_factor"]) for block in populated) < 0.70:
        return False
    return True


def _frontier_qualification(
    discovery: dict[str, Any],
    validation: dict[str, Any],
    holdout: dict[str, Any],
    full: dict[str, Any],
    stress_holdout: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(full["sample_size"]) < 120:
        reasons.append("Amostra total abaixo de 120 trades.")
    if int(validation["sample_size"]) < 15:
        reasons.append("Validacao abaixo de 15 trades.")
    if int(holdout["sample_size"]) < 20:
        reasons.append("Holdout abaixo de 20 trades.")
    if float(discovery["profit_factor"]) < 1.20:
        reasons.append("PF de descoberta abaixo de 1.20.")
    if float(validation["profit_factor"]) < 1.05:
        reasons.append("PF de validacao abaixo de 1.05.")
    if float(holdout["profit_factor"]) < 1.15:
        reasons.append("PF de holdout abaixo de 1.15.")
    if float(full["profit_factor"]) < 1.30:
        reasons.append("PF total liquido abaixo de 1.30.")
    if float(stress_holdout["profit_factor"]) < 1.05:
        reasons.append("PF de holdout estressado abaixo de 1.05.")
    if float(full["max_drawdown"]) > 0.15:
        reasons.append("Drawdown total acima de 15%.")
    populated = [block for block in blocks if int(block["sample_size"]) >= 8]
    if sum(float(block["expectancy"]) > 0 for block in populated) < 3:
        reasons.append("Menos de tres blocos de descoberta positivos.")
    if float(full["ict_score"]) < 70.0:
        reasons.append("ICT total abaixo de B (70).")
    if not bool(full["minimum_filters_passed"]):
        reasons.append("Filtros minimos do ICT nao atendidos.")
    return not reasons, reasons


def search_pair(
    pair: str,
    market: Any,
    context: ContextArrays,
    base_parameters: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
    *,
    cost_fraction: float,
    stress_cost_fraction: float,
) -> dict[str, Any]:
    windows = frontier_windows(len(market.close))
    base_signals = [build_signal(market, parameters) for parameters in base_parameters]
    base_paths = [
        precompute_next_open_paths(
            market,
            signal,
            stop_factor=float(parameters["stop_factor"]),
            risk_reward=float(parameters["risk_reward"]),
        )
        for parameters, signal in zip(base_parameters, base_signals)
    ]
    atr_ratio = market.frame["atr_ratio"].to_numpy(dtype=float)
    discovery_survivors: list[dict[str, Any]] = []
    for overlay in overlays:
        base_index = int(overlay["base_index"])
        signal = apply_context_overlay(
            base_signals[base_index],
            context,
            atr_ratio,
            overlay,
        )
        discovery = _evaluate_paths(
            base_paths[base_index],
            signal,
            windows.discovery,
            cost_fraction,
        )
        blocks = [
            _evaluate_paths(base_paths[base_index], signal, block, cost_fraction)
            for block in windows.stability_blocks
        ]
        if not _frontier_discovery_allowed(discovery, blocks):
            continue
        discovery_survivors.append(
            {
                "overlay": overlay,
                "base_parameters": base_parameters[base_index],
                "discovery": discovery,
                "stability_blocks": blocks,
                "discovery_score": _selection_score(discovery, blocks),
                "signal": signal,
                "paths": base_paths[base_index],
            }
        )
    discovery_survivors.sort(
        key=lambda item: float(item["discovery_score"]),
        reverse=True,
    )
    finalists: list[dict[str, Any]] = []
    for item in discovery_survivors[:80]:
        validation = _evaluate_paths(
            item["paths"],
            item["signal"],
            windows.validation,
            cost_fraction,
        )
        if int(validation["sample_size"]) < 10:
            continue
        if float(validation["profit_factor"]) < 0.90:
            continue
        item["validation"] = validation
        item["pre_holdout_score"] = _validation_score(
            item["discovery"],
            validation,
            item["stability_blocks"],
        )
        finalists.append(item)
    finalists.sort(
        key=lambda item: float(item["pre_holdout_score"]),
        reverse=True,
    )
    if not finalists:
        return {
            "pair": pair,
            "alpha_id": f"{ALPHA_ID}_{pair}",
            "qualified": False,
            "status": "NO_PRE_HOLDOUT_SURVIVOR",
            "candidate_count": len(overlays),
            "discovery_survivors": len(discovery_survivors),
            "holdout_opened": False,
            "qualification_reasons": [
                "Nenhum candidato sobreviveu descoberta e validacao."
            ],
            "winner": None,
        }

    selected = finalists[0]
    holdout = _evaluate_paths(
        selected["paths"],
        selected["signal"],
        windows.holdout,
        cost_fraction,
    )
    stress_holdout = _evaluate_paths(
        selected["paths"],
        selected["signal"],
        windows.holdout,
        stress_cost_fraction,
    )
    full = _evaluate_paths(
        selected["paths"],
        selected["signal"],
        (0, len(market.close)),
        cost_fraction,
    )
    qualified, reasons = _frontier_qualification(
        selected["discovery"],
        selected["validation"],
        holdout,
        full,
        stress_holdout,
        selected["stability_blocks"],
    )
    return {
        "pair": pair,
        "alpha_id": f"{ALPHA_ID}_{pair}",
        "qualified": qualified,
        "status": (
            "QUALIFIED_FOR_MODEL4_REPLAY"
            if qualified
            else "RESEARCH_NOT_QUALIFIED"
        ),
        "candidate_count": len(overlays),
        "discovery_survivors": len(discovery_survivors),
        "validation_finalists": len(finalists),
        "holdout_opened": True,
        "qualification_reasons": reasons,
        "winner": {
            "base_parameters": selected["base_parameters"],
            "context_overlay": selected["overlay"],
            "entry_contract": "SIGNAL_CLOSED_CANDLE_TO_NEXT_CANDLE_OPEN",
            "pre_holdout_score": selected["pre_holdout_score"],
            "discovery": selected["discovery"],
            "stability_blocks": selected["stability_blocks"],
            "validation": selected["validation"],
            "holdout": holdout,
            "stress_holdout": stress_holdout,
            "full_sample": full,
        },
        "pre_holdout_top_five": [
            {
                "base_parameters": item["base_parameters"],
                "context_overlay": item["overlay"],
                "pre_holdout_score": item["pre_holdout_score"],
                "discovery": item["discovery"],
                "validation": item["validation"],
            }
            for item in finalists[:5]
        ],
    }


def run_frontier_research(
    *,
    m3_artifact_path: Path = DEFAULT_M3_ARTIFACT,
    m30_snapshot_path: Path = DEFAULT_M30_SNAPSHOT,
    h1_snapshot_path: Path = DEFAULT_H1_SNAPSHOT,
    h4_snapshot_path: Path = DEFAULT_H4_SNAPSHOT,
    overlays_per_pair: int = 2_500,
    seed: int = 20260726,
    round_trip_cost_bps: float = DEFAULT_ROUND_TRIP_COST_BPS,
    stress_round_trip_cost_bps: float = STRESS_ROUND_TRIP_COST_BPS,
) -> dict[str, Any]:
    m3_artifact = json.loads(m3_artifact_path.read_text(encoding="utf-8"))
    primary = {
        pair: enrich_market(market)
        for pair, market in load_markets_for_timeframe(
            m30_snapshot_path, PRIMARY_TIMEFRAME
        ).items()
    }
    h1 = {
        pair: enrich_market(market)
        for pair, market in load_markets_for_timeframe(h1_snapshot_path, "H1").items()
    }
    h4 = {
        pair: enrich_market(market)
        for pair, market in load_markets_for_timeframe(h4_snapshot_path, "H4").items()
    }
    contexts = build_contexts(primary, h1, h4)
    cost_fraction = float(round_trip_cost_bps) / 10_000.0
    stress_cost_fraction = float(stress_round_trip_cost_bps) / 10_000.0
    results: dict[str, Any] = {}
    for pair in sorted(primary):
        base_parameters = load_base_candidates(m3_artifact, pair)
        if not base_parameters:
            results[pair] = {
                "pair": pair,
                "qualified": False,
                "status": "MISSING_M3_DEVELOPMENT_CANDIDATES",
                "winner": None,
            }
            continue
        overlays = generate_overlay_candidates(
            len(base_parameters),
            overlays_per_pair,
            seed + sum(ord(character) for character in pair),
        )
        results[pair] = search_pair(
            pair,
            primary[pair],
            contexts[pair],
            base_parameters,
            overlays,
            cost_fraction=cost_fraction,
            stress_cost_fraction=stress_cost_fraction,
        )
        result = results[pair]
        winner = result.get("winner") or {}
        full = winner.get("full_sample", {}) if isinstance(winner, dict) else {}
        holdout = winner.get("holdout", {}) if isinstance(winner, dict) else {}
        print(
            json.dumps(
                {
                    "pair": pair,
                    "qualified": result.get("qualified", False),
                    "status": result.get("status"),
                    "family": (winner.get("base_parameters") or {}).get("family"),
                    "overlay": winner.get("context_overlay"),
                    "full_pf": full.get("profit_factor"),
                    "holdout_pf": holdout.get("profit_factor"),
                    "ict": full.get("ict_score"),
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
    qualified_pairs = [
        pair for pair, result in results.items() if bool(result.get("qualified", False))
    ]
    return {
        "schema_version": "1.0",
        "alpha_id": ALPHA_ID,
        "status": "MODEL4_CONTEXTUAL_FRONTIER_COMPLETE",
        "model_destination": MODEL_DESTINATION,
        "operational_model_4_untouched": True,
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_timeframe": PRIMARY_TIMEFRAME,
        "context_timeframes": ["H1", "H4"],
        "entry_contract": "NEXT_CANDLE_OPEN_AFTER_CLOSED_M30_SIGNAL",
        "candles_per_pair": 20_000,
        "overlay_candidates_requested_per_pair": int(overlays_per_pair),
        "random_seed": int(seed),
        "round_trip_cost_bps": float(round_trip_cost_bps),
        "stress_round_trip_cost_bps": float(stress_round_trip_cost_bps),
        "unexplored_dimensions": [
            "completed_h1_h4_context",
            "cross_pair_currency_strength",
            "buy_sell_asymmetry",
            "rolling_volatility_percentile",
            "next_bar_open_execution",
        ],
        "windows": {
            "discovery": "0%-60%",
            "validation": "60%-75%",
            "embargo": "75%-80%",
            "holdout": "80%-100%",
        },
        "guardrail": (
            "MODELO_4_PESQUISA is isolated. MODELO_4_ESPELHO_M1 remains the "
            "only operational M4 contract."
        ),
        "source_artifacts": {
            "m3_development_candidates": m3_artifact_path.as_posix(),
            "m30": m30_snapshot_path.as_posix(),
            "h1": h1_snapshot_path.as_posix(),
            "h4": h4_snapshot_path.as_posix(),
        },
        "qualified_pairs": qualified_pairs,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3-artifact", type=Path, default=DEFAULT_M3_ARTIFACT)
    parser.add_argument("--m30-snapshot", type=Path, default=DEFAULT_M30_SNAPSHOT)
    parser.add_argument("--h1-snapshot", type=Path, default=DEFAULT_H1_SNAPSHOT)
    parser.add_argument("--h4-snapshot", type=Path, default=DEFAULT_H4_SNAPSHOT)
    parser.add_argument("--overlays", type=int, default=2_500)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--round-trip-cost-bps", type=float, default=DEFAULT_ROUND_TRIP_COST_BPS)
    parser.add_argument(
        "--stress-round-trip-cost-bps",
        type=float,
        default=STRESS_ROUND_TRIP_COST_BPS,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = run_frontier_research(
        m3_artifact_path=args.m3_artifact,
        m30_snapshot_path=args.m30_snapshot,
        h1_snapshot_path=args.h1_snapshot,
        h4_snapshot_path=args.h4_snapshot,
        overlays_per_pair=args.overlays,
        seed=args.seed,
        round_trip_cost_bps=args.round_trip_cost_bps,
        stress_round_trip_cost_bps=args.stress_round_trip_cost_bps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "model_destination": payload["model_destination"],
                "operational": payload["operational"],
                "qualified_pairs": payload["qualified_pairs"],
                "output": str(args.output),
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
