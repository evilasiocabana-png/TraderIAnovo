"""Automatic prefix-versus-full lookahead audit for Pattern Miner."""

from __future__ import annotations

import math

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.detectors import CausalEventDetector
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.models import (
    CandleBar,
    CausalityAuditCheck,
    CausalityAuditResult,
    EventRecord,
    MarketEvent,
)


class PatternCausalityAuditor:
    """Recompute selected prefixes and compare their final immutable record."""

    _NUMERIC_FIELDS = (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "spread",
        "real_volume",
        "ema9",
        "ema20",
        "ema50",
        "ema200",
        "rsi14",
        "atr14",
        "adx14",
        "plus_di14",
        "minus_di14",
        "volume_average",
        "volume_relative",
        "volume_zscore",
        "volume_percentile",
    )

    def __init__(self, config: PatternMinerConfig) -> None:
        self.config = config

    def audit(
        self,
        candles: list[CandleBar],
        full_records: list[EventRecord],
        *,
        indices: tuple[int, ...] | None = None,
    ) -> CausalityAuditResult:
        """Prove records at N are identical with and without candles after N."""

        if not candles or len(full_records) != len(candles):
            check = CausalityAuditCheck(-1, False, ("dataset_or_record_count",))
            return CausalityAuditResult(False, (check,))
        selected = indices or self._default_indices(len(candles))
        checks = tuple(
            self._audit_index(candles, full_records[index], index)
            for index in sorted({item for item in selected if 0 <= item < len(candles)})
        )
        return CausalityAuditResult(bool(checks) and all(item.passed for item in checks), checks)

    def _audit_index(
        self,
        candles: list[CandleBar],
        expected: EventRecord,
        index: int,
    ) -> CausalityAuditCheck:
        prefix = candles[: index + 1]
        indicators = IndicatorEngine(self.config).compute(prefix)
        detector = CausalEventDetector(self.config)
        actual = None
        for current in range(len(prefix)):
            actual = detector.process(current, prefix, indicators)
        assert actual is not None
        mismatches = self._compare_records(expected, actual)
        return CausalityAuditCheck(index, not mismatches, tuple(mismatches))

    def _default_indices(self, total: int) -> tuple[int, ...]:
        return tuple(
            min(max(int(total * fraction) - 1, self.config.warmup_candles), total - 1)
            for fraction in self.config.causality_audit_fractions
        )

    def _compare_records(self, expected: EventRecord, actual: EventRecord) -> list[str]:
        mismatches: list[str] = []
        for field_name in self._NUMERIC_FIELDS:
            if not self._same_number(getattr(expected, field_name), getattr(actual, field_name)):
                mismatches.append(field_name)
        for field_name in ("index", "timestamp", "trend_state", "structure_state", "warmup_complete", "session"):
            if getattr(expected, field_name) != getattr(actual, field_name):
                mismatches.append(field_name)
        if self._event_signatures(expected.events) != self._event_signatures(actual.events):
            mismatches.append("events")
        return mismatches

    @classmethod
    def _event_signatures(cls, events: tuple[MarketEvent, ...]) -> tuple[object, ...]:
        return tuple(
            (
                event.event_type,
                event.index,
                event.origin_index,
                event.direction,
                cls._rounded(event.level),
                cls._rounded(event.intensity),
                tuple((key, cls._rounded(value)) for key, value in event.features),
            )
            for event in events
        )

    @staticmethod
    def _same_number(first: object, second: object) -> bool:
        if first is None or second is None:
            return first is second
        return math.isclose(float(first), float(second), rel_tol=1e-12, abs_tol=1e-12)

    @staticmethod
    def _rounded(value: object) -> object:
        if isinstance(value, float):
            return round(value, 12)
        return value
