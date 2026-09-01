"""Promotion, persistence and live shadow tracking for Pattern Miner candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import time
from typing import Iterable

from domain.operational_pattern import (
    OperationalPatternSpec,
    OperationalPatternStatus,
    ShadowStatus,
    SignalCandidate,
    ShadowSignalResult,
)
from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.detectors import CausalEventDetector
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.models import CandleBar, EventRecord, PatternRanking


MODEL_28_ID = "MODELO_28_PATTERN_MINER_SHADOW"
MODEL_28_SHORT_NAME = "M28"
MODEL_28_SOURCE = "REPLAY_PATTERN_MINER"
MODEL_28_EXECUTION_MODE = "DEMO_ADAPTIVE"
MODEL_28_CONTRACT_VERSION = "M28_PATTERN_BRIDGE_V6_EMPIRICAL_CONTRACTS"
MODEL_28_LEGACY_CONTRACT_VERSION = "M28_PATTERN_BRIDGE_V3_COST_AWARE"
MODEL_28_ENTRY_RULE = "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION"


class PatternPromotionValidator:
    """Gate manual promotion with evidence already measured by the Replay."""

    def __init__(
        self,
        minimum_occurrences: int = 100,
        minimum_split_expectancy_r: float = 0.05,
    ) -> None:
        self.minimum_occurrences = minimum_occurrences
        self.minimum_split_expectancy_r = minimum_split_expectancy_r

    def validate(self, ranking: PatternRanking) -> tuple[str, ...]:
        failures: list[str] = []
        if ranking.direction == 0:
            failures.append("DIRECTION_NEUTRAL")
        if ranking.occurrences < self.minimum_occurrences:
            failures.append("INSUFFICIENT_OCCURRENCES")
        if ranking.score <= 0.0:
            failures.append("NON_POSITIVE_SCORE")
        target_atr = _validated_target_atr(ranking)
        split_expectancies = ranking.net_split_expectancies_for_target(target_atr)
        if any(
            value < self.minimum_split_expectancy_r
            for value in split_expectancies
        ):
            failures.append("NET_SPLIT_EXPECTANCY_TOO_LOW")
        return tuple(failures)


class OperationalPatternStore:
    """Atomic JSON registry for immutable promoted pattern versions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> tuple[OperationalPatternSpec, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return tuple(
                OperationalPatternSpec.from_dict(item)
                for item in payload.get("specs", ())
            )
        except (OSError, ValueError, TypeError, KeyError):
            return ()

    def save(self, specs: Iterable[OperationalPatternSpec]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "m28-operational-pattern-v1",
            "model_id": MODEL_28_ID,
            "execution_mode": MODEL_28_EXECUTION_MODE,
            "specs": [item.to_dict() for item in specs],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        _replace_with_retry(temporary, self.path)

    def promote(
        self,
        ranking: PatternRanking,
        *,
        symbol: str,
        timeframe: str,
        max_event_distance: int,
        source_cache_key: str,
    ) -> OperationalPatternSpec:
        failures = PatternPromotionValidator().validate(ranking)
        if failures:
            raise ValueError(
                "Padrao nao aprovado para promocao: " + ", ".join(failures)
            )
        specs = list(self.load())
        setup_id = f"{symbol.upper()}_{ranking.pattern_id.replace('-', '_')}"
        target_atr = _validated_target_atr(ranking)
        candidate = _spec_from_ranking(
            ranking,
            setup_id=setup_id,
            version=1,
            symbol=symbol,
            timeframe=timeframe,
            max_event_distance=max_event_distance,
            source_cache_key=source_cache_key,
            target_atr=target_atr,
        )
        existing = [item for item in specs if item.setup_id == setup_id]
        for item in reversed(existing):
            if _same_contract(item, candidate):
                return item
        version = max((item.version for item in existing), default=0) + 1
        candidate = replace(candidate, version=version)
        specs.append(candidate)
        self.save(specs)
        return candidate

    def set_shadow(self, versioned_id: str, enabled: bool) -> OperationalPatternSpec:
        specs = list(self.load())
        updated: OperationalPatternSpec | None = None
        for index, item in enumerate(specs):
            if item.versioned_id != versioned_id:
                continue
            updated = replace(
                item,
                shadow_status=ShadowStatus.RUNNING if enabled else ShadowStatus.OFF,
            )
            specs[index] = updated
            break
        if updated is None:
            raise KeyError(f"OperationalPatternSpec nao encontrado: {versioned_id}")
        self.save(specs)
        return updated


@dataclass(slots=True)
class _TrackerState:
    next_event: int = 0
    start_index: int | None = None
    last_event_index: int | None = None


class LivePatternTracker:
    """Track multiple promoted state machines without touching execution."""

    def __init__(self, specs: Iterable[OperationalPatternSpec] = ()) -> None:
        self.set_specs(specs)

    def set_specs(self, specs: Iterable[OperationalPatternSpec]) -> None:
        self.specs = tuple(
            item
            for item in specs
            if item.status == OperationalPatternStatus.OPERATIONAL_CANDIDATE
            and item.shadow_status == ShadowStatus.RUNNING
        )
        self.states = {item.versioned_id: _TrackerState() for item in self.specs}

    def consume(self, record: EventRecord) -> tuple[SignalCandidate, ...]:
        signals: list[SignalCandidate] = []
        for spec in self.specs:
            state = self.states[spec.versioned_id]
            if (
                state.last_event_index is not None
                and record.index - state.last_event_index > spec.max_distance_between_events
            ):
                self.states[spec.versioned_id] = state = _TrackerState()
            for event in record.events:
                expected = spec.event_sequence[state.next_event]
                if event.event_type != expected:
                    if event.event_type == spec.event_sequence[0]:
                        state.next_event = 1
                        state.start_index = record.index
                        state.last_event_index = record.index
                    continue
                if not _direction_matches(spec.direction, event.direction):
                    continue
                if state.next_event > 0 and state.last_event_index is not None:
                    gap = record.index - state.last_event_index
                    bucket = spec.event_gap_buckets[state.next_event - 1]
                    if not _gap_matches(bucket, gap):
                        if gap > _gap_upper_bound(bucket):
                            self.states[spec.versioned_id] = state = _TrackerState()
                        continue
                if state.next_event == 0:
                    state.start_index = record.index
                state.next_event += 1
                state.last_event_index = record.index
                if state.next_event < len(spec.event_sequence):
                    continue
                signal = (
                    _signal_from_completion(spec, record, state.start_index)
                    if _context_matches(spec, record)
                    else None
                )
                if signal is not None:
                    signals.append(signal)
                self.states[spec.versioned_id] = state = _TrackerState()
        return tuple(signals)

    def state_label(self, versioned_id: str) -> str:
        spec = next((item for item in self.specs if item.versioned_id == versioned_id), None)
        if spec is None:
            return "DISABLED"
        state = self.states[versioned_id]
        return f"WAITING_{spec.event_sequence[state.next_event]}"


class LivePatternEngine:
    """Use the exact Replay indicator and event engines on incoming closed bars."""

    def __init__(
        self,
        config: PatternMinerConfig | None = None,
        specs: Iterable[OperationalPatternSpec] = (),
    ) -> None:
        self.config = config or PatternMinerConfig()
        self.indicators = IndicatorEngine(self.config)
        self.detector = CausalEventDetector(self.config)
        self.tracker = LivePatternTracker(specs)
        self.candles: list[CandleBar] = []
        self.records: list[EventRecord] = []

    def consume_closed_candle(
        self,
        candle: CandleBar,
    ) -> tuple[EventRecord, tuple[SignalCandidate, ...]]:
        if self.candles and candle.timestamp <= self.candles[-1].timestamp:
            raise ValueError("LivePatternEngine exige candle fechado novo e cronologico.")
        normalized = CandleBar(
            index=len(self.candles),
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            spread=candle.spread,
            real_volume=candle.real_volume,
        )
        self.candles.append(normalized)
        frame = self.indicators.compute(self.candles)
        record = self.detector.process(normalized.index, self.candles, frame)
        self.records.append(record)
        return record, self.tracker.consume(record)


class ShadowSignalJournal:
    """Persist and evaluate hypothetical M28 signals without trade execution."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> tuple[ShadowSignalResult, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return tuple(
                ShadowSignalResult.from_dict(item)
                for item in payload.get("signals", ())
            )
        except (OSError, ValueError, TypeError):
            return ()

    def record(self, signals: Iterable[SignalCandidate]) -> tuple[ShadowSignalResult, ...]:
        rows = list(self.load())
        known = {item.pattern_occurrence_id for item in rows}
        for signal in signals:
            if signal.pattern_occurrence_id in known:
                continue
            context = signal.context()
            try:
                max_holding_candles = int(
                    context.get("max_holding_candles", 0) or 0
                )
            except (TypeError, ValueError):
                max_holding_candles = 0
            rows.append(
                ShadowSignalResult(
                    pattern_occurrence_id=signal.pattern_occurrence_id,
                    setup_id=signal.setup_id,
                    setup_version=signal.setup_version,
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    direction=signal.direction,
                    opened_at=signal.datetime.isoformat(),
                    entry_reference=signal.entry_reference,
                    stop_reference=signal.stop_reference,
                    target_reference=signal.target_reference,
                    max_holding_candles=max_holding_candles,
                    entry_filled=(
                        str(context.get("entry_rule", "")) != MODEL_28_ENTRY_RULE
                    ),
                    cost_rule=str(context.get("cost_rule", "")),
                )
            )
        self._save(rows)
        return tuple(rows)

    def evaluate(
        self,
        candle: CandleBar,
        *,
        symbol: str = "XAUUSD",
    ) -> tuple[ShadowSignalResult, ...]:
        rows = list(self.load())
        changed = False
        for index, item in enumerate(rows):
            if item.status != "OPEN" or item.symbol != symbol:
                continue
            if candle.timestamp.isoformat() <= item.opened_at:
                continue
            if not item.entry_filled:
                stop_distance = abs(item.entry_reference - item.stop_reference)
                target_distance = abs(item.target_reference - item.entry_reference)
                if stop_distance <= 0.0 or target_distance <= 0.0:
                    continue
                entry = float(candle.open)
                if item.direction == "BUY":
                    stop = entry - stop_distance
                    target = entry + target_distance
                else:
                    stop = entry + stop_distance
                    target = entry - target_distance
                spread_price = (
                    max(float(candle.spread or 0.0), 0.0)
                    * _historical_spread_point_size(item.symbol)
                    if item.cost_rule == "RECORDED_ENTRY_SPREAD_ONLY"
                    else 0.0
                )
                item = replace(
                    item,
                    entry_reference=entry,
                    stop_reference=stop,
                    target_reference=target,
                    entry_filled=True,
                    cost_r=spread_price / stop_distance,
                )
                rows[index] = item
                changed = True
            risk = abs(item.entry_reference - item.stop_reference)
            if risk <= 0.0:
                continue
            if item.direction == "BUY":
                stopped = candle.low <= item.stop_reference
                targeted = candle.high >= item.target_reference
            else:
                stopped = candle.high >= item.stop_reference
                targeted = candle.low <= item.target_reference
            candles_observed = item.candles_observed + 1
            if stopped:
                # Conservative collision rule: stop wins if both occur in one candle.
                status = "AMBIGUOUS_STOP" if targeted else "STOP"
                exit_reference = item.stop_reference
                result_r = -1.0 - item.cost_r
            elif targeted:
                status = "TARGET"
                exit_reference = item.target_reference
                result_r = (
                    abs(item.target_reference - item.entry_reference) / risk
                    - item.cost_r
                )
            elif (
                item.max_holding_candles > 0
                and candles_observed >= item.max_holding_candles
            ):
                status = "TIME_EXIT"
                exit_reference = float(candle.close)
                reward_r = abs(
                    item.target_reference - item.entry_reference
                ) / risk
                marked_r = (
                    (exit_reference - item.entry_reference) / risk
                    if item.direction == "BUY"
                    else (item.entry_reference - exit_reference) / risk
                )
                result_r = max(-1.0, min(reward_r, marked_r)) - item.cost_r
            else:
                rows[index] = replace(
                    item,
                    candles_observed=candles_observed,
                )
                changed = True
                continue
            rows[index] = replace(
                item,
                status=status,
                closed_at=candle.timestamp.isoformat(),
                exit_reference=exit_reference,
                result_r=result_r,
                candles_observed=candles_observed,
            )
            changed = True
        if changed:
            self._save(rows)
        return tuple(rows)

    def _save(self, rows: Iterable[ShadowSignalResult]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": "m28-shadow-journal-v1",
                    "signals": [item.to_dict() for item in rows],
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        _replace_with_retry(temporary, self.path)


def _historical_spread_point_size(symbol: str) -> float:
    normalized = str(symbol or "").upper()
    if normalized.endswith("JPY"):
        return 0.001
    if normalized in {"XAUUSD", "BTCUSD"}:
        return 0.01
    return 0.00001


def _replace_with_retry(source: Path, target: Path) -> None:
    """Tolerate short OneDrive/antivirus locks without losing atomic writes."""

    for attempt in range(20):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 19:
                # OneDrive may allow rewriting an open file while denying rename.
                target.write_bytes(source.read_bytes())
                source.unlink(missing_ok=True)
                return
            time.sleep(0.1)


def _validated_target_atr(ranking: PatternRanking) -> float:
    fp1_floor = min(ranking.net_split_expectancies_for_target(1.0))
    fp2_floor = min(ranking.net_split_expectancies_for_target(2.0))
    if fp2_floor != fp1_floor:
        return 2.0 if fp2_floor > fp1_floor else 1.0
    return (
        2.0
        if ranking.first_passage_2_expectancy_net
        > ranking.first_passage_1_expectancy_net
        else 1.0
    )


def _spec_from_ranking(
    ranking: PatternRanking,
    *,
    setup_id: str,
    version: int,
    symbol: str,
    timeframe: str,
    max_event_distance: int,
    source_cache_key: str,
    target_atr: float,
) -> OperationalPatternSpec:
    discovery, validation, oos = ranking.net_split_expectancies_for_target(
        target_atr
    )
    return OperationalPatternSpec.created_now(
        setup_id=setup_id,
        pattern_id=ranking.pattern_id,
        version=version,
        symbol=symbol,
        timeframe=timeframe,
        direction="BUY" if ranking.direction > 0 else "SELL",
        event_sequence=ranking.sequence,
        event_gap_buckets=ranking.gap_buckets,
        max_distance_between_events=max_event_distance,
        context_filters=(("warmup_complete", True),),
        entry_rule=MODEL_28_ENTRY_RULE,
        stop_rule="REPLAY_FIRST_PASSAGE_MINUS_1_ATR",
        target_rule=f"REPLAY_FIRST_PASSAGE_PLUS_{target_atr:g}_ATR",
        target_atr=target_atr,
        expiration_rule="EXPIRE_AT_NEXT_CLOSED_CANDLE",
        minimum_score=ranking.score,
        minimum_occurrences=ranking.occurrences,
        discovery_metrics=(
            ("performance", discovery),
            ("horizon_return_atr", ranking.discovery_performance),
        ),
        validation_metrics=(
            ("performance", validation),
            ("horizon_return_atr", ranking.validation_performance),
        ),
        oos_metrics=(
            ("performance", oos),
            ("horizon_return_atr", ranking.oos_performance),
        ),
        status=OperationalPatternStatus.OPERATIONAL_CANDIDATE,
        shadow_status=ShadowStatus.OFF,
        source_cache_key=source_cache_key,
        stop_atr=1.0,
        contract_version=MODEL_28_LEGACY_CONTRACT_VERSION,
    )


def _same_contract(left: OperationalPatternSpec, right: OperationalPatternSpec) -> bool:
    return (
        left.pattern_id,
        left.event_sequence,
        left.event_gap_buckets,
        left.direction,
        left.entry_rule,
        left.stop_rule,
        left.target_rule,
        left.expiration_rule,
        left.context_filters,
        left.stop_atr,
        left.target_atr,
        left.contract_version,
        left.source_cache_key,
    ) == (
        right.pattern_id,
        right.event_sequence,
        right.event_gap_buckets,
        right.direction,
        right.entry_rule,
        right.stop_rule,
        right.target_rule,
        right.expiration_rule,
        right.context_filters,
        right.stop_atr,
        right.target_atr,
        right.contract_version,
        right.source_cache_key,
    )


def _direction_matches(direction: str, event_direction: int) -> bool:
    if event_direction == 0:
        return True
    return event_direction > 0 if direction == "BUY" else event_direction < 0


def _gap_matches(bucket: str, gap: int) -> bool:
    if bucket == "same candle":
        return gap == 0
    if bucket == "1-2 candles":
        return 1 <= gap <= 2
    if bucket == "3-5 candles":
        return 3 <= gap <= 5
    if bucket == "6-12 candles":
        return 6 <= gap <= 12
    return gap >= 0


def _gap_upper_bound(bucket: str) -> int:
    return {
        "same candle": 0,
        "1-2 candles": 2,
        "3-5 candles": 5,
        "6-12 candles": 12,
    }.get(bucket, 12)


def _signal_from_completion(
    spec: OperationalPatternSpec,
    record: EventRecord,
    start_index: int | None,
) -> SignalCandidate | None:
    if not record.warmup_complete or record.atr14 is None or record.atr14 <= 0.0:
        return None
    entry = record.close
    atr = record.atr14
    stop_atr = max(float(spec.stop_atr), 0.0)
    if stop_atr <= 0.0:
        return None
    if spec.direction == "BUY":
        stop = entry - atr * stop_atr
        target = entry + atr * spec.target_atr
    else:
        stop = entry + atr * stop_atr
        target = entry - atr * spec.target_atr
    return SignalCandidate(
        setup_id=spec.setup_id,
        setup_version=spec.version,
        symbol=spec.symbol,
        timeframe=spec.timeframe,
        datetime=record.timestamp,
        direction=spec.direction,
        entry_reference=entry,
        stop_reference=stop,
        target_reference=target,
        confidence=spec.minimum_score,
        pattern_occurrence_id=(
            f"{spec.versioned_id}:{start_index if start_index is not None else record.index}:"
            f"{record.index}"
        ),
        events_confirmed=spec.event_sequence,
        context_snapshot=(
            ("ema9", record.ema9),
            ("ema20", record.ema20),
            ("ema50", record.ema50),
            ("ema200", record.ema200),
            ("rsi14", record.rsi14),
            ("atr14", record.atr14),
            ("adx14", record.adx14),
            ("structure", record.structure_state),
            ("session", record.session),
            ("pattern_id", spec.pattern_id),
            ("entry_rule", spec.entry_rule),
            ("stop_rule", spec.stop_rule),
            ("target_rule", spec.target_rule),
            ("expiration_rule", spec.expiration_rule),
            ("max_holding_candles", spec.max_holding_candles),
            ("cost_rule", spec.cost_rule),
        ),
    )


def _context_matches(spec: OperationalPatternSpec, record: EventRecord) -> bool:
    """Apply the same causal context buckets used by the v4 research gate."""

    for name, expected in spec.context_filters:
        if name == "scope" and str(expected).upper() == "ALL":
            continue
        if name == "warmup_complete":
            if bool(record.warmup_complete) != bool(expected):
                return False
            continue
        observed = _context_value(str(name), spec.direction, record)
        if observed is None or str(observed) != str(expected):
            return False
    return True


def _context_value(name: str, direction: str, record: EventRecord) -> str | None:
    event_direction = 1 if direction == "BUY" else -1
    if name == "session":
        return str(record.session or "N/D")
    if name == "trend":
        return _context_alignment(record.trend_state, event_direction)
    if name == "structure":
        return _context_alignment(record.structure_state, event_direction)
    if name == "adx":
        return _context_bucket(record.adx14, 20.0, 30.0)
    if name == "rsi":
        return _context_bucket(record.rsi14, 30.0, 70.0)
    if name == "volume":
        return _context_bucket(record.volume_relative, 0.8, 1.2)
    return None


def _context_alignment(state: str, direction: int) -> str:
    normalized = str(state or "neutral").lower()
    if normalized == "neutral":
        return "NEUTRAL"
    aligned = (direction > 0 and normalized == "bullish") or (
        direction < 0 and normalized == "bearish"
    )
    return "ALIGNED" if aligned else "COUNTER"


def _context_bucket(
    value: float | None,
    lower: float,
    upper: float,
) -> str:
    if value is None:
        return "N/D"
    if value < lower:
        return "LOW"
    if value < upper:
        return "MID"
    return "HIGH"
