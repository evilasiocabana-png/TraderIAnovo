"""Central configuration for the causal XAUUSD Pattern Miner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json


@dataclass(frozen=True, slots=True)
class PatternMinerConfig:
    """All research thresholds used by the Pattern Miner."""

    schema_version: str = "xau-pattern-miner-v3-cost-aware-next-open"
    warmup_candles: int = 200
    ema_periods: tuple[int, ...] = (9, 20, 50, 200)
    rsi_period: int = 14
    atr_period: int = 14
    adx_period: int = 14
    volume_window: int = 20
    swing_left: int = 2
    swing_right: int = 2
    equal_level_tolerance_atr: float = 0.10
    displacement_body_atr: float = 1.00
    displacement_range_atr: float = 1.25
    displacement_body_ratio: float = 0.60
    displacement_volume_relative: float = 1.10
    order_block_lookback: int = 5
    adx_high_threshold: float = 25.0
    atr_expansion_ratio: float = 1.20
    atr_compression_ratio: float = 0.80
    volume_expansion_ratio: float = 1.50
    min_pattern_length: int = 2
    max_pattern_length: int = 5
    max_event_distance: int = 12
    min_pattern_occurrences: int = 20
    max_candidate_patterns: int = 300
    ranking_limit: int = 100
    outcome_horizons: tuple[int, ...] = (1, 3, 5, 10, 20, 50, 100)
    first_passage_targets_atr: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0)
    discovery_fraction: float = 0.60
    validation_fraction: float = 0.20
    execution_friction_r: float = 0.50
    operational_min_occurrences: int = 100
    operational_min_split_expectancy_r: float = 0.05
    causality_audit_fractions: tuple[float, ...] = (0.60, 0.999)
    session_asia_start_utc: int = 0
    session_london_start_utc: int = 7
    session_new_york_start_utc: int = 13
    session_end_utc: int = 21

    def fingerprint(self) -> str:
        """Return a stable cache fingerprint for every research threshold."""

        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
