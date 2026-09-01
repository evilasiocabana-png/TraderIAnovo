"""Versioned contracts between Pattern Miner research and adaptive execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OperationalPatternStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    OPERATIONAL_CANDIDATE = "OPERATIONAL_CANDIDATE"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    REJECTED = "REJECTED"


class ShadowStatus(str, Enum):
    OFF = "OFF"
    RUNNING = "RUNNING"


@dataclass(frozen=True, slots=True)
class OperationalPatternSpec:
    """Immutable promoted research pattern consumed by Model 28."""

    setup_id: str
    pattern_id: str
    version: int
    symbol: str
    timeframe: str
    direction: str
    event_sequence: tuple[str, ...]
    event_gap_buckets: tuple[str, ...]
    max_distance_between_events: int
    context_filters: tuple[tuple[str, Any], ...]
    entry_rule: str
    stop_rule: str
    target_rule: str
    target_atr: float
    expiration_rule: str
    minimum_score: float
    minimum_occurrences: int
    discovery_metrics: tuple[tuple[str, float], ...]
    validation_metrics: tuple[tuple[str, float], ...]
    oos_metrics: tuple[tuple[str, float], ...]
    created_at: str
    status: OperationalPatternStatus
    shadow_status: ShadowStatus = ShadowStatus.OFF
    source_cache_key: str = ""
    stop_atr: float = 1.0
    contract_version: str = ""
    evidence_tier: str = "LEGACY"
    adaptive_rank: int = 0
    pattern_family: str = ""
    selection_score: float = 0.0
    repeat_limit: int = 1
    repeat_window_candles: int = 100
    repeat_probability: float = 0.0
    repeat_basis: str = "FIRST_OCCURRENCE_ONLY"
    repeat_statistics: tuple[tuple[str, float], ...] = ()
    max_holding_candles: int = 100
    cost_rule: str = ""
    geometry_method: str = ""
    geometry_statistics: tuple[tuple[str, float], ...] = ()

    @property
    def versioned_id(self) -> str:
        return f"{self.setup_id}_v{self.version}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["shadow_status"] = self.shadow_status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OperationalPatternSpec":
        values = dict(payload)
        values["event_sequence"] = tuple(values.get("event_sequence", ()))
        values["event_gap_buckets"] = tuple(values.get("event_gap_buckets", ()))
        for key in (
            "context_filters",
            "discovery_metrics",
            "validation_metrics",
            "oos_metrics",
            "repeat_statistics",
            "geometry_statistics",
        ):
            values[key] = tuple(tuple(item) for item in values.get(key, ()))
        values["status"] = OperationalPatternStatus(values["status"])
        values["shadow_status"] = ShadowStatus(values.get("shadow_status", "OFF"))
        return cls(**values)

    @classmethod
    def created_now(cls, **values: Any) -> "OperationalPatternSpec":
        values.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        return cls(**values)


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    """Causal signal candidate that may become a Demo plan after all gates."""

    setup_id: str
    setup_version: int
    symbol: str
    timeframe: str
    datetime: datetime
    direction: str
    entry_reference: float
    stop_reference: float
    target_reference: float
    confidence: float
    pattern_occurrence_id: str
    events_confirmed: tuple[str, ...]
    context_snapshot: tuple[tuple[str, Any], ...]
    status: str = "SHADOW_SIGNAL"

    def context(self) -> dict[str, Any]:
        return dict(self.context_snapshot)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["datetime"] = self.datetime.isoformat()
        return payload


@dataclass(frozen=True, slots=True)
class ShadowSignalResult:
    """Persisted hypothetical lifecycle of one Model 28 signal."""

    pattern_occurrence_id: str
    setup_id: str
    setup_version: int
    symbol: str
    timeframe: str
    direction: str
    opened_at: str
    entry_reference: float
    stop_reference: float
    target_reference: float
    status: str = "OPEN"
    closed_at: str | None = None
    exit_reference: float | None = None
    result_r: float | None = None
    max_holding_candles: int = 0
    candles_observed: int = 0
    entry_filled: bool = True
    cost_rule: str = ""
    cost_r: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ShadowSignalResult":
        return cls(**payload)
