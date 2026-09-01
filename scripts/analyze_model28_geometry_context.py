"""Learn one causal execution contract for every Replay-discovered M28 pattern."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.model28_pattern_miner_shadow import (
    synchronize_model28_replay_contracts,
)
from application.xau_pattern_miner_service import XauPatternMinerService
from domain.market_universe import MT5_RESEARCH_MARKETS
from replay.pattern_miner.models import CandleBar, EventRecord, PatternOccurrence


MARKETS = (
    "XAUUSD",
    *(symbol for symbol in MT5_RESEARCH_MARKETS if symbol != "XAUUSD"),
)
OUTPUT_PATH = (
    ROOT
    / ".traderia"
    / "research"
    / "model28_optimizer"
    / "empirical_pattern_contracts_v6.json"
)
EMPIRICAL_STOP_QUANTILES = (0.50, 0.65, 0.80)
EMPIRICAL_TARGET_QUANTILES = (0.35, 0.50, 0.65)
EMPIRICAL_QUANTILE_PROFILES = tuple(
    zip(EMPIRICAL_STOP_QUANTILES, EMPIRICAL_TARGET_QUANTILES)
)
EMPIRICAL_HOLDING_CANDLES = (5, 10, 20, 50, 100)
MAX_HOLDING_CANDLES = max(EMPIRICAL_HOLDING_CANDLES)
MIN_EMPIRICAL_DISTANCE_ATR = 0.05
RECORDED_SPREAD_COST_RULE = "RECORDED_ENTRY_SPREAD_ONLY"
MIN_DISCOVERY = 60
MIN_VALIDATION = 20
MIN_OOS = 20
MIN_EXPECTANCY_R = 0.05
ADAPTIVE_VALIDATION_POOL = 12
DISCOVERY_PATTERN_POOL = 100
OPERATIONAL_PATTERNS_PER_MARKET = 3
REPEAT_EPISODE_GAP_CANDLES = MAX_HOLDING_CANDLES
REPEAT_MAX_POSITION = 5
MIN_REPEAT_EPISODES = 10
MIN_REPEAT_REACH_PROBABILITY = 0.50


@dataclass(slots=True)
class _Aggregate:
    trades: int = 0
    total: float = 0.0
    total_square: float = 0.0
    wins: int = 0
    targets: int = 0
    stops: int = 0
    time_exits: int = 0
    total_cost_r: float = 0.0

    def add(self, value: float, status: str, cost_r: float = 0.0) -> None:
        self.trades += 1
        self.total += value
        self.total_square += value * value
        self.wins += int(value > 0.0)
        self.targets += int(status == "TARGET")
        self.stops += int(status in {"STOP", "AMBIGUOUS_STOP"})
        self.time_exits += int(status == "TIME_EXIT")
        self.total_cost_r += max(float(cost_r), 0.0)


@dataclass(frozen=True, slots=True)
class _TradeSample:
    signal_index: int
    exit_index: int
    result_r: float
    status: str
    signal_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class _EmpiricalGeometry:
    """Pattern-specific barriers learned only from Discovery occurrences."""

    stop_atr: float
    target_atr: float
    max_holding_candles: int
    stop_quantile: float
    target_quantile: float

    @property
    def rr(self) -> float:
        return self.target_atr / self.stop_atr


def _bucket(value: float | None, limits: tuple[float, float], labels: tuple[str, str, str]) -> str:
    if value is None:
        return "N/D"
    if value < limits[0]:
        return labels[0]
    if value < limits[1]:
        return labels[1]
    return labels[2]


def _alignment(state: str, direction: int) -> str:
    normalized = str(state or "neutral").lower()
    if normalized == "neutral":
        return "NEUTRAL"
    aligned = (direction > 0 and normalized == "bullish") or (
        direction < 0 and normalized == "bearish"
    )
    return "ALIGNED" if aligned else "COUNTER"


def _context_variants(record: EventRecord, direction: int) -> tuple[tuple[tuple[str, str], ...], ...]:
    fields = {
        "session": str(record.session or "N/D"),
        "trend": _alignment(record.trend_state, direction),
        "structure": _alignment(record.structure_state, direction),
        "adx": _bucket(record.adx14, (20.0, 30.0), ("LOW", "MID", "HIGH")),
        "rsi": _bucket(record.rsi14, (30.0, 70.0), ("LOW", "MID", "HIGH")),
        "volume": _bucket(
            record.volume_relative,
            (0.8, 1.2),
            ("LOW", "MID", "HIGH"),
        ),
    }
    names = (
        ("session",),
        ("trend",),
        ("structure",),
        ("rsi",),
        ("adx",),
        ("volume",),
        ("session", "trend"),
        ("trend", "structure"),
        ("trend", "rsi"),
        ("trend", "adx"),
        ("trend", "volume"),
        ("structure", "rsi"),
        ("session", "trend", "adx"),
    )
    variants: list[tuple[tuple[str, str], ...]] = [(('scope', 'ALL'),)]
    for keys in names:
        values = tuple((key, fields[key]) for key in keys)
        if all(value != "N/D" for _, value in values):
            variants.append(values)
    return tuple(variants)


def _quantile(values: Iterable[float], probability: float) -> float:
    """Return a deterministic linearly interpolated empirical quantile."""

    ordered = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(float(probability), 1.0)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _symbol_point_size(symbol: str) -> float:
    """Translate the MT5 integer spread stored in rates into price distance."""

    normalized = str(symbol or "").upper()
    if normalized.endswith("JPY"):
        return 0.001
    if normalized in {"XAUUSD", "BTCUSD"}:
        return 0.01
    return 0.00001


def _path_excursions(
    occurrence: PatternOccurrence,
    candles: list[CandleBar],
    records: list[EventRecord],
    holding_candles: int,
) -> tuple[float, float] | None:
    """Measure causal post-pattern MFE/MAE from the next tradable bar open."""

    entry_index = occurrence.end_index + 1
    end_index = entry_index + int(holding_candles)
    if entry_index >= len(candles) or end_index > len(candles):
        return None
    atr = records[occurrence.end_index].atr14
    entry = candles[entry_index].open
    if atr is None or atr <= 0.0 or entry <= 0.0 or occurrence.direction == 0:
        return None
    future = candles[entry_index:end_index]
    if occurrence.direction > 0:
        favorable = max(item.high - entry for item in future)
        adverse = max(entry - item.low for item in future)
    else:
        favorable = max(entry - item.low for item in future)
        adverse = max(item.high - entry for item in future)
    return max(adverse, 0.0) / atr, max(favorable, 0.0) / atr


def _empirical_geometry_candidates(
    occurrences: Iterable[PatternOccurrence],
    candles: list[CandleBar],
    records: list[EventRecord],
) -> tuple[_EmpiricalGeometry, ...]:
    """Create pattern-specific barriers from Discovery MAE/MFE distributions."""

    rows = tuple(occurrences)
    candidates: dict[tuple[float, float, int], _EmpiricalGeometry] = {}
    for holding in EMPIRICAL_HOLDING_CANDLES:
        excursions = [
            measured
            for occurrence in rows
            if (measured := _path_excursions(occurrence, candles, records, holding))
            is not None
        ]
        if len(excursions) < MIN_DISCOVERY:
            continue
        adverse_values = [item[0] for item in excursions]
        favorable_values = [item[1] for item in excursions]
        for stop_quantile, target_quantile in EMPIRICAL_QUANTILE_PROFILES:
            stop_atr = max(
                _quantile(adverse_values, stop_quantile),
                MIN_EMPIRICAL_DISTANCE_ATR,
            )
            target_atr = max(
                _quantile(favorable_values, target_quantile),
                MIN_EMPIRICAL_DISTANCE_ATR,
            )
            identity = (round(stop_atr, 6), round(target_atr, 6), holding)
            candidates.setdefault(
                identity,
                _EmpiricalGeometry(
                    stop_atr=identity[0],
                    target_atr=identity[1],
                    max_holding_candles=holding,
                    stop_quantile=stop_quantile,
                    target_quantile=target_quantile,
                ),
            )
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (
                item.max_holding_candles,
                item.stop_atr,
                item.target_atr,
            ),
        )
    )


def _trade_result(
    occurrence: PatternOccurrence,
    candles: list[CandleBar],
    records: list[EventRecord],
    geometry: _EmpiricalGeometry,
    symbol: str,
) -> tuple[float | None, str, int, float] | None:
    entry_index = occurrence.end_index + 1
    if entry_index >= len(candles):
        return None
    atr = records[occurrence.end_index].atr14
    entry = candles[entry_index].open
    if atr is None or atr <= 0.0 or entry <= 0.0:
        return None
    direction = occurrence.direction
    stop_distance = geometry.stop_atr * atr
    target_distance = geometry.target_atr * atr
    if stop_distance <= 0.0 or target_distance <= 0.0:
        return None
    spread_points = max(float(records[entry_index].spread or 0.0), 0.0)
    spread_price = spread_points * _symbol_point_size(symbol)
    cost_r = spread_price / stop_distance
    maturity_index = entry_index + geometry.max_holding_candles
    end_index = min(len(candles), maturity_index)
    for bar_index in range(entry_index, end_index):
        bar = candles[bar_index]
        if direction > 0:
            target_hit = bar.high >= entry + target_distance
            stop_hit = bar.low <= entry - stop_distance
        else:
            target_hit = bar.low <= entry - target_distance
            stop_hit = bar.high >= entry + stop_distance
        if target_hit and stop_hit:
            return -1.0 - cost_r, "AMBIGUOUS_STOP", bar_index, cost_r
        if stop_hit:
            return -1.0 - cost_r, "STOP", bar_index, cost_r
        if target_hit:
            return geometry.rr - cost_r, "TARGET", bar_index, cost_r
    if end_index <= entry_index:
        return None
    if len(candles) < maturity_index:
        return None, "OPEN", len(candles) - 1, cost_r
    exit_price = candles[maturity_index - 1].close
    marked_r = direction * (exit_price - entry) / stop_distance
    return (
        max(-1.0, min(geometry.rr, marked_r)) - cost_r,
        "TIME_EXIT",
        maturity_index - 1,
        cost_r,
    )


def _metrics(values: _Aggregate | None) -> dict[str, object]:
    values = values or _Aggregate()
    count = values.trades
    average = values.total / count if count else 0.0
    if count >= 2:
        variance = max(
            (values.total_square - values.total * values.total / count)
            / (count - 1),
            0.0,
        )
        deviation = math.sqrt(variance)
    else:
        deviation = 0.0
    lower_80 = average - 1.281552 * deviation / math.sqrt(count) if count else 0.0
    return {
        "trades": count,
        "expectancy_r": average,
        "net_r": values.total,
        "win_rate": values.wins / count if count else 0.0,
        "target_rate": values.targets / count if count else 0.0,
        "stop_rate": values.stops / count if count else 0.0,
        "time_exit_rate": values.time_exits / count if count else 0.0,
        "mean_recorded_cost_r": values.total_cost_r / count if count else 0.0,
        "lower_80_expectancy_r": lower_80,
    }


def _context_json(context: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return {key: value for key, value in context}


def _passes_split(metrics: dict[str, object], minimum_trades: int) -> bool:
    return (
        int(metrics["trades"]) >= minimum_trades
        and float(metrics["expectancy_r"]) >= MIN_EXPECTANCY_R
        and float(metrics["lower_80_expectancy_r"]) > 0.0
    )


def _event_family(event_type: str) -> str:
    value = str(event_type).upper()
    if "FVG" in value:
        return "FVG"
    if any(token in value for token in ("SWING", "BOS", "CHOCH", "HH", "HL", "LH", "LL", "SWEEP")):
        return "STRUCTURE"
    if "ORDER_BLOCK" in value:
        return "ORDER_BLOCK"
    if "RSI" in value:
        return "MOMENTUM"
    if any(token in value for token in ("ATR", "DISPLACEMENT")):
        return "VOLATILITY"
    if "VOLUME" in value:
        return "VOLUME"
    return value


def _pattern_family(events: Iterable[str], direction: str) -> str:
    collapsed: list[str] = []
    for event in events:
        family = _event_family(event)
        if not collapsed or collapsed[-1] != family:
            collapsed.append(family)
    label = f"{direction}:{'>'.join(collapsed)}"
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10].upper()
    return f"FAM-{digest}:{label}"


def _adaptive_evidence(candidate: dict[str, object]) -> tuple[float, float, int]:
    discovery = dict(candidate["discovery"])
    validation = dict(candidate["validation"])
    oos = dict(candidate["oos"])
    d_value = float(discovery["expectancy_r"])
    v_value = float(validation["expectancy_r"])
    o_value = float(oos["expectancy_r"])
    positive_splits = sum(value > 0.0 for value in (d_value, v_value, o_value))
    validation_sample = min(float(validation["trades"]) / MIN_VALIDATION, 1.0)
    sample_factor = math.sqrt(max(validation_sample, 0.0))
    instability = abs(d_value - v_value)
    # OOS is reported and may certify a frozen contract, but never tunes or
    # ranks it. This keeps the final chronological block genuinely unseen.
    raw_score = 0.35 * d_value + 0.65 * v_value - 0.15 * instability
    adaptive_score = raw_score * (0.35 + 0.65 * sample_factor)
    logistic = 1.0 / (1.0 + math.exp(-adaptive_score))
    confidence = max(
        0.05,
        min(0.95, logistic * (0.50 + 0.50 * sample_factor)),
    )
    return adaptive_score, confidence, positive_splits


def _repeat_profile(
    samples: Iterable[_TradeSample],
    *,
    gap_candles: int = REPEAT_EPISODE_GAP_CANDLES,
) -> dict[str, object]:
    """Describe whether one exact setup recurs alone, in pairs, triples or longer."""

    ordered = sorted(samples, key=lambda item: item.signal_index)
    episodes: list[list[_TradeSample]] = []
    for sample in ordered:
        previous = episodes[-1][-1] if episodes else None
        if (
            previous is not None
            and previous.signal_time is not None
            and sample.signal_time is not None
        ):
            starts_new_episode = (
                sample.signal_time - previous.signal_time
                > timedelta(minutes=5 * max(int(gap_candles), 1))
            )
        else:
            starts_new_episode = bool(
                previous is not None
                and sample.signal_index - previous.signal_index
                > max(int(gap_candles), 1)
            )
        if (
            not episodes
            or starts_new_episode
        ):
            episodes.append([sample])
        else:
            episodes[-1].append(sample)
    length_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "5_plus": 0}
    for episode in episodes:
        bucket = str(len(episode)) if len(episode) <= 4 else "5_plus"
        length_counts[bucket] += 1
    episode_count = len(episodes)
    modal_bucket = min(
        length_counts,
        key=lambda name: (
            -length_counts[name],
            5 if name == "5_plus" else int(name),
        ),
    ) if episode_count else "1"
    modal_count = 5 if modal_bucket == "5_plus" else int(modal_bucket)
    positions: dict[str, dict[str, object]] = {}
    for position in range(1, REPEAT_MAX_POSITION + 1):
        values = [
            episode[position - 1]
            for episode in episodes
            if len(episode) >= position
        ]
        aggregate = _Aggregate()
        for sample in values:
            aggregate.add(sample.result_r, sample.status)
        position_metrics = _metrics(aggregate)
        reached_previous = (
            episode_count
            if position == 1
            else sum(len(episode) >= position - 1 for episode in episodes)
        )
        position_metrics["reach_probability"] = (
            len(values) / episode_count if episode_count else 0.0
        )
        position_metrics["continuation_probability"] = (
            len(values) / reached_previous if reached_previous else 0.0
        )
        positions[str(position)] = position_metrics
    median_repeat_count = 1
    for position in range(2, REPEAT_MAX_POSITION + 1):
        if (
            float(positions[str(position)]["reach_probability"])
            < MIN_REPEAT_REACH_PROBABILITY
        ):
            break
        median_repeat_count = position
    return {
        "episodes": episode_count,
        "length_counts": length_counts,
        "modal_repeat_count": modal_count,
        "median_repeat_count": median_repeat_count,
        "modal_probability": (
            length_counts[modal_bucket] / episode_count if episode_count else 0.0
        ),
        "pair_or_more_probability": (
            sum(len(episode) >= 2 for episode in episodes) / episode_count
            if episode_count
            else 0.0
        ),
        "triple_or_more_probability": (
            sum(len(episode) >= 3 for episode in episodes) / episode_count
            if episode_count
            else 0.0
        ),
        "positions": positions,
    }


def _recommended_repeat_limit(profile: dict[str, object]) -> int:
    """Use the median run length, but never extrapolate a thin or weak position."""

    episodes = int(profile.get("episodes", 0) or 0)
    if episodes < MIN_REPEAT_EPISODES:
        return 1
    median = max(
        1,
        min(int(profile.get("median_repeat_count", 1) or 1), REPEAT_MAX_POSITION),
    )
    positions = dict(profile.get("positions", {}) or {})
    supported = 1
    for position in range(2, median + 1):
        metrics = dict(positions.get(str(position), {}) or {})
        if (
            int(metrics.get("trades", 0) or 0) < MIN_REPEAT_EPISODES
            or float(metrics.get("reach_probability", 0.0) or 0.0)
            < MIN_REPEAT_REACH_PROBABILITY
            or float(metrics.get("expectancy_r", 0.0) or 0.0)
            < MIN_EXPECTANCY_R
            or float(metrics.get("lower_80_expectancy_r", 0.0) or 0.0) <= 0.0
        ):
            break
        supported = position
    return supported


def _analyze_market(symbol: str) -> dict[str, object]:
    service = XauPatternMinerService.for_symbol(symbol)
    try:
        service.ensure_loaded()
        state = service.restore_cache()
        if state.status.value != "FINISHED":
            service.start("Maximum")
            state = service.run_to_end()
        if state.result is None or state.status.value != "FINISHED":
            raise RuntimeError(f"Replay indisponivel: {state.status.value}")
        records = service.engine.records
        candles = service.engine.candles
        miner = service.engine.pattern_miner
        tokens = miner._event_stream(records)
        discovery_end = state.result.discovery_end_index
        validation_end = state.result.validation_end_index
        discovery_tokens = [token for token in tokens if token.index < discovery_end]
        discovery_counts = miner._count_patterns(discovery_tokens)
        candidate_rows = [
            (key, count)
            for key, count in discovery_counts.items()
            if count >= MIN_DISCOVERY
        ]
        candidate_rows.sort(key=lambda item: (-item[1], item[0].pattern_id))
        candidate_rows = candidate_rows[
            : min(miner.config.max_candidate_patterns, DISCOVERY_PATTERN_POOL)
        ]
        keys = {key for key, _ in candidate_rows}
        occurrences = miner._collect_occurrences(
            tokens,
            keys,
            discovery_end,
            validation_end,
        )
        context_cache: dict[
            tuple[int, int], tuple[tuple[tuple[str, str], ...], ...]
        ] = {}
        discovery_by_pattern: dict[str, list[PatternOccurrence]] = defaultdict(list)
        discovery_context_counts: dict[
            tuple[str, tuple[tuple[str, str], ...]],
            int,
        ] = defaultdict(int)
        for key, rows in occurrences.items():
            for occurrence in rows:
                if occurrence.split != "DISCOVERY":
                    continue
                discovery_by_pattern[key.pattern_id].append(occurrence)
                record = records[occurrence.end_index]
                context_key = (occurrence.end_index, occurrence.direction)
                contexts = context_cache.setdefault(
                    context_key,
                    _context_variants(record, occurrence.direction),
                )
                for context in contexts:
                    discovery_context_counts[(key.pattern_id, context)] += 1

        key_by_pattern_id = {key.pattern_id: key for key in keys}
        discovery_eligible: list[dict[str, object]] = []
        for pattern_id, group_rows in discovery_by_pattern.items():
            if len(group_rows) < MIN_DISCOVERY:
                continue
            eligible_contexts = {
                context
                for (candidate_pattern_id, context), count in discovery_context_counts.items()
                if candidate_pattern_id == pattern_id and count >= MIN_DISCOVERY
            }
            if not eligible_contexts:
                continue
            for geometry in _empirical_geometry_candidates(
                group_rows,
                candles,
                records,
            ):
                aggregates = {
                    context: _Aggregate()
                    for context in eligible_contexts
                }
                occupied_until = {
                    context: -1
                    for context in eligible_contexts
                }
                for occurrence in sorted(group_rows, key=lambda item: item.end_index):
                    result = _trade_result(
                        occurrence,
                        candles,
                        records,
                        geometry,
                        symbol,
                    )
                    if result is None:
                        continue
                    value, status, exit_index, cost_r = result
                    contexts = context_cache[
                        (occurrence.end_index, occurrence.direction)
                    ]
                    entry_index = occurrence.end_index + 1
                    for context in contexts:
                        if context not in eligible_contexts:
                            continue
                        if entry_index <= occupied_until[context]:
                            continue
                        occupied_until[context] = exit_index
                        if value is not None:
                            aggregates[context].add(value, status, cost_r)
                for context, aggregate in aggregates.items():
                    discovery = _metrics(aggregate)
                    if not _passes_split(discovery, MIN_DISCOVERY):
                        continue
                    discovery_eligible.append(
                        {
                            "symbol": symbol,
                            "pattern_id": pattern_id,
                            "context": _context_json(context),
                            "_context": context,
                            "entry_rule": "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION",
                            "stop_rule": (
                                f"DISCOVERY_MAE_Q{int(geometry.stop_quantile * 100):02d}_ATR"
                            ),
                            "target_rule": (
                                f"DISCOVERY_MFE_Q{int(geometry.target_quantile * 100):02d}_ATR"
                            ),
                            "expiration_rule": (
                                f"FULL_EXIT_AFTER_{geometry.max_holding_candles}_M5_CANDLES"
                            ),
                            "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
                            "stop_atr": geometry.stop_atr,
                            "target_atr": geometry.target_atr,
                            "rr": geometry.rr,
                            "max_holding_candles": geometry.max_holding_candles,
                            "stop_quantile": geometry.stop_quantile,
                            "target_quantile": geometry.target_quantile,
                            "cost_rule": RECORDED_SPREAD_COST_RULE,
                            "discovery": discovery,
                        }
                    )
        discovery_eligible.sort(
            key=lambda item: (
                -float(item["discovery"]["lower_80_expectancy_r"]),
                -float(item["discovery"]["expectancy_r"]),
                -int(item["discovery"]["trades"]),
                str(item["pattern_id"]),
                tuple(sorted(item["context"].items())),
                float(item["stop_atr"]),
                float(item["target_atr"]),
                int(item["max_holding_candles"]),
            )
        )

        for discovery_rank, candidate in enumerate(discovery_eligible, start=1):
            candidate["_discovery_rank"] = discovery_rank

        shortlist = [
            {key: value for key, value in candidate.items() if not key.startswith("_")}
            for candidate in discovery_eligible[:5]
        ]

        evaluated_candidates: list[dict[str, object]] = []
        for source_candidate in discovery_eligible[:ADAPTIVE_VALIDATION_POOL]:
            candidate = dict(source_candidate)
            selected_context = candidate.pop("_context")
            discovery_rank = int(candidate.pop("_discovery_rank"))
            selected_key = key_by_pattern_id[str(candidate["pattern_id"])]
            direction = "BUY" if selected_key.direction > 0 else "SELL"
            geometry = _EmpiricalGeometry(
                stop_atr=float(candidate["stop_atr"]),
                target_atr=float(candidate["target_atr"]),
                max_holding_candles=int(candidate["max_holding_candles"]),
                stop_quantile=float(candidate["stop_quantile"]),
                target_quantile=float(candidate["target_quantile"]),
            )

            def evaluate_split(
                split: str,
                initial_active_until: int,
            ) -> tuple[_Aggregate, int, list[_TradeSample]]:
                aggregate = _Aggregate()
                recurrence_samples: list[_TradeSample] = []
                occupied_until = initial_active_until
                for occurrence in occurrences.get(selected_key, ()):
                    if occurrence.split != split:
                        continue
                    record = records[occurrence.end_index]
                    if selected_context not in _context_variants(
                        record,
                        occurrence.direction,
                    ):
                        continue
                    result = _trade_result(
                        occurrence,
                        candles,
                        records,
                        geometry,
                        symbol,
                    )
                    if result is None:
                        continue
                    value, status, exit_index, cost_r = result
                    if value is not None:
                        recurrence_samples.append(
                            _TradeSample(
                                signal_index=occurrence.end_index,
                                exit_index=exit_index,
                                result_r=value,
                                status=status,
                                signal_time=candles[occurrence.end_index].timestamp,
                            )
                        )
                    # Recurrence describes every completed causal occurrence,
                    # exactly as the live detector sees it. Aggregate
                    # performance remains execution-realistic and excludes a
                    # new position while the previous one is still active.
                    if occurrence.end_index + 1 <= occupied_until:
                        continue
                    occupied_until = exit_index
                    if value is not None:
                        aggregate.add(value, status, cost_r)
                return aggregate, occupied_until, recurrence_samples

            discovery_aggregate, discovery_active_until, discovery_samples = (
                evaluate_split("DISCOVERY", -1)
            )
            candidate["discovery"] = _metrics(discovery_aggregate)
            validation_aggregate, validation_active_until, validation_samples = evaluate_split(
                "VALIDATION",
                discovery_active_until,
            )
            validation = _metrics(validation_aggregate)
            oos_aggregate, _, oos_samples = evaluate_split(
                "OOS",
                validation_active_until,
            )
            oos = _metrics(oos_aggregate)
            validation_passed = _passes_split(validation, MIN_VALIDATION)
            oos_passed = _passes_split(oos, MIN_OOS)
            strict_approved = validation_passed and oos_passed
            candidate.update(
                {
                    "events": list(selected_key.sequence),
                    "gaps": list(selected_key.gaps),
                    "direction": direction,
                    "pattern_family": _pattern_family(selected_key.sequence, direction),
                    "discovery_rank": discovery_rank,
                    "validation": validation,
                    "validation_passed": validation_passed,
                    "oos": oos,
                    "oos_evaluated": True,
                    "oos_passed": oos_passed,
                    "approved": strict_approved,
                    "robust_floor_r": min(
                        float(candidate["discovery"]["expectancy_r"]),
                        float(validation["expectancy_r"]),
                        float(oos["expectancy_r"]),
                    ),
                }
            )
            adaptive_score, confidence, positive_splits = _adaptive_evidence(candidate)
            repeat_analysis = {
                "episode_gap_candles": geometry.max_holding_candles,
                "discovery": _repeat_profile(
                    discovery_samples,
                    gap_candles=geometry.max_holding_candles,
                ),
                "validation": _repeat_profile(
                    validation_samples,
                    gap_candles=geometry.max_holding_candles,
                ),
                "oos": _repeat_profile(
                    oos_samples,
                    gap_candles=geometry.max_holding_candles,
                ),
                "all": _repeat_profile(
                    (*discovery_samples, *validation_samples, *oos_samples),
                    gap_candles=geometry.max_holding_candles,
                ),
            }
            repeat_limit = _recommended_repeat_limit(
                dict(repeat_analysis["all"])
            )
            repeat_probability = float(
                dict(repeat_analysis["all"]).get("pair_or_more_probability", 0.0)
                or 0.0
            )
            candidate.update(
                {
                    "adaptive_score": adaptive_score,
                    "selection_confidence": confidence,
                    "positive_splits": positive_splits,
                    "repeat_analysis": repeat_analysis,
                    "repeat_limit": repeat_limit,
                    "repeat_window_candles": geometry.max_holding_candles,
                    "repeat_probability": repeat_probability,
                    "repeat_basis": (
                        "MEDIAN_REACH_50_WITH_ROBUST_POSITIVE_POSITION_EXPECTANCY"
                    ),
                }
            )
            evaluated_candidates.append(candidate)

        evaluated_candidates.sort(
            key=lambda item: (
                -int(bool(item["approved"])),
                -int(bool(item["validation_passed"])),
                -float(item["adaptive_score"]),
                -float(item["validation"]["expectancy_r"]),
                int(item["discovery_rank"]),
            )
        )
        operational_contracts: list[dict[str, object]] = []
        selected_families: set[tuple[str, str]] = set()
        for candidate in evaluated_candidates:
            family_key = (str(candidate["pattern_family"]), str(candidate["direction"]))
            if family_key in selected_families:
                continue
            operational = dict(candidate)
            operational["adaptive_rank"] = len(operational_contracts) + 1
            operational["operational_tier"] = (
                "VALIDATED" if operational["approved"] else "EXPLORATION_DEMO"
            )
            operational_contracts.append(operational)
            selected_families.add(family_key)
            if len(operational_contracts) >= OPERATIONAL_PATTERNS_PER_MARKET:
                break

        selected_contract = operational_contracts[0] if operational_contracts else None
        strict_approved = next(
            (item for item in evaluated_candidates if item["approved"]),
            None,
        )
        return {
            "symbol": symbol,
            "candles": len(candles),
            "discovered_patterns": len(discovery_counts),
            "candidate_patterns": len(keys),
            "discovery_eligible": len(discovery_eligible),
            "discovery_shortlist": shortlist,
            "adaptive_candidates_evaluated": len(evaluated_candidates),
            "adaptive_shortlist": evaluated_candidates[:5],
            "operational_contracts": operational_contracts,
            "selected_contract": selected_contract,
            "validation_passed": bool(strict_approved),
            "oos_evaluated": bool(evaluated_candidates),
            "approved": strict_approved is not None,
        }
    finally:
        service.release()
        del service
        gc.collect()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main(markets: Iterable[str] = MARKETS) -> int:
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    selected_markets = tuple(markets)
    for index, symbol in enumerate(selected_markets, start=1):
        market_started = time.perf_counter()
        print(
            f"[{index:02d}/{len(selected_markets)}] {symbol}: "
            "contratos empiricos por padrao...",
            flush=True,
        )
        try:
            result = _analyze_market(symbol)
            results.append(result)
            print(
                f"[{index:02d}/{len(selected_markets)}] {symbol}: "
                f"{result['discovery_eligible']} elegiveis na descoberta, "
                f"validacao={'OK' if result['validation_passed'] else 'FALHOU'}, "
                f"OOS={'OK' if result['approved'] else 'NAO APROVADO'}, "
                f"{time.perf_counter() - market_started:.1f}s",
                flush=True,
            )
        except Exception as exc:
            failures.append({"symbol": symbol, "error": str(exc)})
            print(f"[{index:02d}/{len(selected_markets)}] {symbol}: FALHA - {exc}", flush=True)
    approved = [
        candidate
        for result in results
        for candidate in result["operational_contracts"]
        if candidate["approved"]
    ]
    operational = [
        candidate
        for result in results
        for candidate in result["operational_contracts"]
    ]
    operational_markets = sorted({str(item["symbol"]) for item in operational})
    payload = {
        "schema_version": "model28-empirical-pattern-contracts-v6-research",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_registry_changed": True,
        "method": {
            "entry": "NEXT_BAR_OPEN",
            "holding_candidates_candles": list(EMPIRICAL_HOLDING_CANDLES),
            "unresolved": "MARK_TO_MARKET_TIME_EXIT",
            "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
            "stop_quantiles": list(EMPIRICAL_STOP_QUANTILES),
            "target_quantiles": list(EMPIRICAL_TARGET_QUANTILES),
            "paired_quantile_profiles": [
                {"stop": stop, "target": target}
                for stop, target in EMPIRICAL_QUANTILE_PROFILES
            ],
            "discovery_pattern_pool": DISCOVERY_PATTERN_POOL,
            "universal_stop_grid": False,
            "universal_rr_grid": False,
            "cost_rule": RECORDED_SPREAD_COST_RULE,
            "spread_point_size": {
                "FOREX": 0.00001,
                "JPY_PAIRS": 0.001,
                "XAUUSD": 0.01,
                "BTCUSD": 0.01,
            },
            "commission_available_in_history": False,
            "swap_available_in_history": False,
            "minimum_split_trades": [MIN_DISCOVERY, MIN_VALIDATION, MIN_OOS],
            "minimum_expectancy_r": MIN_EXPECTANCY_R,
            "adaptive_validation_pool": ADAPTIVE_VALIDATION_POOL,
            "operational_patterns_per_market": OPERATIONAL_PATTERNS_PER_MARKET,
            "selection_uses_validation": True,
            "selection_uses_oos_for_demo_ranking": False,
            "oos_is_final_report_and_certification_only": True,
            "geometry_is_frozen_before_validation": True,
            "selection_policy": (
                "VALIDATED_FIRST_THEN_DISTINCT_FAMILY_ADAPTIVE_DEMO_PORTFOLIO"
            ),
            "validation_and_oos_require_positive_lower_80_bound": True,
            "one_open_trade_per_contract": True,
            "one_order_per_pattern_occurrence": True,
            "outcome_confirmations_before_entry": 0,
            "repeat_episode_gap": "CONTRACT_MAX_HOLDING_CANDLES",
            "repeat_max_position": REPEAT_MAX_POSITION,
            "repeat_minimum_episodes": MIN_REPEAT_EPISODES,
            "repeat_minimum_reach_probability": MIN_REPEAT_REACH_PROBABILITY,
            "repeat_minimum_expectancy_r": MIN_EXPECTANCY_R,
            "repeat_requires_positive_lower_80_bound": True,
            "repeat_policy": (
                "FIRST_OCCURRENCE_ALWAYS_THEN_MEDIAN_RUN_WITH_ROBUST_POSITION_EDGE"
            ),
            "incomplete_end_of_sample_trades_are_excluded": True,
        },
        "markets": results,
        "approved_total": len(approved),
        "approved_contracts": sorted(
            approved,
            key=lambda item: -float(item["robust_floor_r"]),
        ),
        "operational_total": len(operational),
        "operational_market_total": len(operational_markets),
        "operational_markets": operational_markets,
        "operational_contracts": sorted(
            operational,
            key=lambda item: (str(item["symbol"]), int(item["adaptive_rank"])),
        ),
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(OUTPUT_PATH, payload)
    activated = synchronize_model28_replay_contracts(report_path=OUTPUT_PATH)
    print(
        f"Concluido: {len(approved)} contrato(s) OOS aprovado(s), "
        f"{len(operational)} contrato(s) adaptativo(s) em {len(operational_markets)} "
        f"mercado(s), {payload['elapsed_seconds']}s; {len(activated)} ativado(s) no M28 Demo.",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
