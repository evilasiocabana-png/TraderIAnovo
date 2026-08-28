"""Contracts shared by the causal replay and Pattern Miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PatternReplayStatus(str, Enum):
    """Lifecycle states exposed to the Replay UI."""

    EMPTY = "EMPTY"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class ReplaySpeed(str, Enum):
    """Processing modes supported by the Replay UI."""

    VISUAL = "Visual"
    FAST = "Fast"
    MAXIMUM = "Maximum"


@dataclass(frozen=True, slots=True)
class CandleBar:
    """Immutable closed market candle used by research only."""

    index: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float
    real_volume: float


@dataclass(frozen=True, slots=True)
class MarketEvent:
    """A causal event plus its quantitative characteristics."""

    event_type: str
    index: int
    origin_index: int
    direction: int = 0
    level: float | None = None
    intensity: float | None = None
    features: tuple[tuple[str, object], ...] = ()

    def feature_map(self) -> dict[str, object]:
        return dict(self.features)


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Causal candle snapshot stored for mining."""

    index: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float
    real_volume: float
    ema9: float | None
    ema20: float | None
    ema50: float | None
    ema200: float | None
    rsi14: float | None
    atr14: float | None
    adx14: float | None
    plus_di14: float | None
    minus_di14: float | None
    volume_average: float | None
    volume_relative: float | None
    volume_zscore: float | None
    volume_percentile: float | None
    trend_state: str
    structure_state: str
    warmup_complete: bool
    session: str
    events: tuple[MarketEvent, ...] = ()

    @property
    def event_types(self) -> tuple[str, ...]:
        return tuple(event.event_type for event in self.events)


@dataclass(frozen=True, slots=True)
class PatternOccurrence:
    """One completed sequence of causal events."""

    pattern_id: str
    sequence: tuple[str, ...]
    gap_buckets: tuple[str, ...]
    direction: int
    start_index: int
    end_index: int
    event_indices: tuple[int, ...]
    split: str


@dataclass(frozen=True, slots=True)
class HorizonOutcome:
    """Forward result measured after a completed pattern."""

    horizon: int
    return_points: float
    return_percent: float
    return_atr: float
    mfe_points: float
    mfe_atr: float
    mae_points: float
    mae_atr: float


@dataclass(frozen=True, slots=True)
class FirstPassageOutcome:
    """Which directional barrier was reached first."""

    target_atr: float
    status: str
    candles_to_hit: int | None


@dataclass(frozen=True, slots=True)
class OccurrenceOutcome:
    """All forward-only measurements for one occurrence."""

    occurrence: PatternOccurrence
    horizons: tuple[HorizonOutcome, ...]
    first_passage: tuple[FirstPassageOutcome, ...]


@dataclass(frozen=True, slots=True)
class PatternRanking:
    """Aggregated out-of-sample-aware metrics for one pattern."""

    pattern_id: str
    sequence: tuple[str, ...]
    gap_buckets: tuple[str, ...]
    direction: int
    occurrences: int
    frequency: float
    mfe_mean_atr: float
    mfe_median_atr: float
    mae_mean_atr: float
    mae_median_atr: float
    return_mean_atr: float
    return_median_atr: float
    first_passage_1_atr: float
    first_passage_2_atr: float
    expectancy: float
    discovery_performance: float
    validation_performance: float
    oos_performance: float
    score: float

    @property
    def direction_label(self) -> str:
        if self.direction > 0:
            return "UP"
        if self.direction < 0:
            return "DOWN"
        return "NEUTRAL"

    @property
    def display_sequence(self) -> str:
        parts = [self.sequence[0]]
        for gap, event_type in zip(self.gap_buckets, self.sequence[1:]):
            parts.append(f"[{gap}]")
            parts.append(event_type)
        return " -> ".join(parts)


@dataclass(frozen=True, slots=True)
class CausalityAuditCheck:
    """One full-history versus prefix-only causality comparison."""

    index: int
    passed: bool
    mismatches: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CausalityAuditResult:
    """Automatic proof that future candles do not alter past records."""

    passed: bool
    checks: tuple[CausalityAuditCheck, ...] = ()


@dataclass(frozen=True, slots=True)
class PatternMinerResult:
    """Final immutable research output."""

    rankings: tuple[PatternRanking, ...] = ()
    discovered_patterns: int = 0
    candidate_patterns: int = 0
    total_occurrences: int = 0
    discovery_end_index: int = 0
    validation_end_index: int = 0
    cache_key: str = ""
    causality_audit: CausalityAuditResult | None = None


@dataclass(frozen=True, slots=True)
class PatternReplayState:
    """Read-only state consumed by Streamlit."""

    status: PatternReplayStatus
    speed: ReplaySpeed
    dataset_loaded: bool
    dataset_name: str
    symbol: str
    timeframe: str
    total_candles: int
    current_index: int
    current_record: EventRecord | None
    event_counts: dict[str, int]
    recent_events: tuple[MarketEvent, ...]
    active_patterns: int
    completed_pattern_occurrences: int
    result: PatternMinerResult | None
    logs: tuple[str, ...]
    error: str = ""
    cache_restored: bool = False

    @property
    def processed_candles(self) -> int:
        return max(self.current_index + 1, 0)

    @property
    def progress(self) -> float:
        if self.total_candles <= 0:
            return 0.0
        return min(max(self.processed_candles / self.total_candles, 0.0), 1.0)


@dataclass(slots=True)
class IndicatorFrame:
    """Columnar causal indicator storage."""

    ema9: list[float | None] = field(default_factory=list)
    ema20: list[float | None] = field(default_factory=list)
    ema50: list[float | None] = field(default_factory=list)
    ema200: list[float | None] = field(default_factory=list)
    rsi14: list[float | None] = field(default_factory=list)
    atr14: list[float | None] = field(default_factory=list)
    adx14: list[float | None] = field(default_factory=list)
    plus_di14: list[float | None] = field(default_factory=list)
    minus_di14: list[float | None] = field(default_factory=list)
    volume_average: list[float | None] = field(default_factory=list)
    volume_relative: list[float | None] = field(default_factory=list)
    volume_zscore: list[float | None] = field(default_factory=list)
    volume_percentile: list[float | None] = field(default_factory=list)
    atr_relative: list[float | None] = field(default_factory=list)
