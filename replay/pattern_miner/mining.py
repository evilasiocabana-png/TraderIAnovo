"""Pattern discovery, outcome analysis, and robust ranking."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import math
from statistics import mean, median

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.models import (
    CandleBar,
    EventRecord,
    FirstPassageOutcome,
    HorizonOutcome,
    OccurrenceOutcome,
    PatternMinerResult,
    PatternOccurrence,
    PatternRanking,
)


@dataclass(frozen=True, slots=True)
class _Token:
    index: int
    event_type: str
    direction: int


@dataclass(frozen=True, slots=True)
class _PatternKey:
    sequence: tuple[str, ...]
    gaps: tuple[str, ...]
    direction: int

    @property
    def pattern_id(self) -> str:
        raw = "|".join(self.sequence) + "|" + "|".join(self.gaps) + f"|{self.direction}"
        return "PAT-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


class OutcomeEngine:
    """Measure future outcomes without modifying past event records."""

    def __init__(self, config: PatternMinerConfig) -> None:
        self.config = config

    def evaluate(
        self,
        occurrence: PatternOccurrence,
        candles: list[CandleBar],
        records: list[EventRecord],
    ) -> OccurrenceOutcome | None:
        """Evaluate one occurrence using candles strictly after completion."""

        end = occurrence.end_index
        if end < 0 or end >= len(candles):
            return None
        entry_index = end + 1
        if entry_index >= len(candles):
            return None
        atr = records[end].atr14
        # The live market order only exists after the completion candle closes.
        # The next bar open is the earliest OHLC price the historical engine can
        # use without crediting movement that happened before execution.
        entry = candles[entry_index].open
        if atr is None or atr <= 0.0 or entry <= 0.0:
            return None
        direction = occurrence.direction or self._inferred_direction(occurrence.sequence)
        if direction == 0:
            return None
        horizons: list[HorizonOutcome] = []
        for horizon in self.config.outcome_horizons:
            last = entry_index + horizon - 1
            if last >= len(candles):
                continue
            future = candles[entry_index : last + 1]
            exit_price = candles[last].close
            directional_return = direction * (exit_price - entry)
            if direction > 0:
                mfe = max(item.high - entry for item in future)
                mae = max(entry - item.low for item in future)
            else:
                mfe = max(entry - item.low for item in future)
                mae = max(item.high - entry for item in future)
            horizons.append(
                HorizonOutcome(
                    horizon=horizon,
                    return_points=directional_return,
                    return_percent=100.0 * directional_return / entry,
                    return_atr=directional_return / atr,
                    mfe_points=max(mfe, 0.0),
                    mfe_atr=max(mfe, 0.0) / atr,
                    mae_points=max(mae, 0.0),
                    mae_atr=max(mae, 0.0) / atr,
                )
            )
        first_passage = tuple(
            self._first_passage(
                candles,
                entry_index,
                entry,
                atr,
                direction,
                target,
            )
            for target in self.config.first_passage_targets_atr
        )
        return OccurrenceOutcome(
            occurrence=occurrence,
            horizons=tuple(horizons),
            first_passage=first_passage,
        )

    @staticmethod
    def _first_passage(
        candles: list[CandleBar],
        entry_index: int,
        entry: float,
        atr: float,
        direction: int,
        target_atr: float,
    ) -> FirstPassageOutcome:
        favorable = target_atr * atr
        adverse = atr
        limit = min(len(candles), entry_index + 100)
        for index in range(entry_index, limit):
            bar = candles[index]
            if direction > 0:
                favorable_hit = bar.high >= entry + favorable
                adverse_hit = bar.low <= entry - adverse
            else:
                favorable_hit = bar.low <= entry - favorable
                adverse_hit = bar.high >= entry + adverse
            if favorable_hit and adverse_hit:
                return FirstPassageOutcome(
                    target_atr,
                    "AMBIGUOUS",
                    index - entry_index + 1,
                )
            if favorable_hit:
                return FirstPassageOutcome(
                    target_atr,
                    "SUCCESS",
                    index - entry_index + 1,
                )
            if adverse_hit:
                return FirstPassageOutcome(
                    target_atr,
                    "FAILURE",
                    index - entry_index + 1,
                )
        return FirstPassageOutcome(target_atr, "UNRESOLVED", None)

    @staticmethod
    def _inferred_direction(sequence: tuple[str, ...]) -> int:
        upward = ("_UP", "HH", "HL", "ABOVE", "SWEEP_LOW", "OVERSOLD")
        downward = ("_DOWN", "LH", "LL", "BELOW", "SWEEP_HIGH", "OVERBOUGHT")
        for event_type in reversed(sequence):
            if any(token in event_type for token in upward):
                return 1
            if any(token in event_type for token in downward):
                return -1
        return 0


class PatternMiner:
    """Discover bounded event sequences and rank them chronologically."""

    def __init__(self, config: PatternMinerConfig) -> None:
        self.config = config
        self.outcome_engine = OutcomeEngine(config)

    def mine(
        self,
        records: list[EventRecord],
        candles: list[CandleBar],
        *,
        cache_key: str = "",
    ) -> PatternMinerResult:
        """Run discovery on 60%, then validate candidates on 20% + 20%."""

        if not records:
            return PatternMinerResult(cache_key=cache_key)
        total = len(records)
        discovery_end = int(total * self.config.discovery_fraction)
        validation_end = int(
            total
            * (self.config.discovery_fraction + self.config.validation_fraction)
        )
        tokens = self._event_stream(records)
        discovery_tokens = [token for token in tokens if token.index < discovery_end]
        counts = self._count_patterns(discovery_tokens)
        discovered_patterns = len(counts)
        candidates = [
            (key, count)
            for key, count in counts.items()
            if count >= self.config.min_pattern_occurrences
        ]
        candidates.sort(key=lambda item: (-item[1], item[0].pattern_id))
        candidate_keys = {
            key for key, _ in candidates[: self.config.max_candidate_patterns]
        }
        occurrences = self._collect_occurrences(
            tokens,
            candidate_keys,
            discovery_end,
            validation_end,
        )
        rankings = self._rank(occurrences, candles, records)
        return PatternMinerResult(
            rankings=tuple(rankings[: self.config.ranking_limit]),
            discovered_patterns=discovered_patterns,
            candidate_patterns=len(candidate_keys),
            total_occurrences=sum(len(items) for items in occurrences.values()),
            discovery_end_index=discovery_end,
            validation_end_index=validation_end,
            cache_key=cache_key,
        )

    @staticmethod
    def _event_stream(records: list[EventRecord]) -> list[_Token]:
        tokens: list[_Token] = []
        for record in records:
            for event in record.events:
                tokens.append(_Token(record.index, event.event_type, event.direction))
        return tokens

    def _count_patterns(self, tokens: list[_Token]) -> Counter[_PatternKey]:
        counts: Counter[_PatternKey] = Counter()
        for end_position in range(len(tokens)):
            for length in range(self.config.min_pattern_length, self.config.max_pattern_length + 1):
                start_position = end_position - length + 1
                if start_position < 0:
                    break
                window = tokens[start_position : end_position + 1]
                key = self._pattern_key(window)
                if key is not None:
                    counts[key] += 1
        return counts

    def _collect_occurrences(
        self,
        tokens: list[_Token],
        candidate_keys: set[_PatternKey],
        discovery_end: int,
        validation_end: int,
    ) -> dict[_PatternKey, list[PatternOccurrence]]:
        result: dict[_PatternKey, list[PatternOccurrence]] = defaultdict(list)
        for end_position in range(len(tokens)):
            for length in range(self.config.min_pattern_length, self.config.max_pattern_length + 1):
                start_position = end_position - length + 1
                if start_position < 0:
                    break
                window = tokens[start_position : end_position + 1]
                key = self._pattern_key(window)
                if key not in candidate_keys:
                    continue
                split = self._split(window[-1].index, discovery_end, validation_end)
                result[key].append(
                    PatternOccurrence(
                        pattern_id=key.pattern_id,
                        sequence=key.sequence,
                        gap_buckets=key.gaps,
                        direction=key.direction,
                        start_index=window[0].index,
                        end_index=window[-1].index,
                        event_indices=tuple(token.index for token in window),
                        split=split,
                    )
                )
        return result

    def _pattern_key(self, window: list[_Token]) -> _PatternKey | None:
        gaps = [window[index].index - window[index - 1].index for index in range(1, len(window))]
        if any(gap < 0 or gap > self.config.max_event_distance for gap in gaps):
            return None
        directions = {token.direction for token in window if token.direction != 0}
        if len(directions) > 1:
            return None
        direction = next(iter(directions), 0)
        if direction == 0:
            return None
        if len({token.event_type for token in window}) == 1:
            return None
        return _PatternKey(
            sequence=tuple(token.event_type for token in window),
            gaps=tuple(self._gap_bucket(gap) for gap in gaps),
            direction=direction,
        )

    def _rank(
        self,
        occurrences: dict[_PatternKey, list[PatternOccurrence]],
        candles: list[CandleBar],
        records: list[EventRecord],
    ) -> list[PatternRanking]:
        rankings: list[PatternRanking] = []
        for key, pattern_occurrences in occurrences.items():
            outcomes = [
                outcome
                for occurrence in pattern_occurrences
                if (outcome := self.outcome_engine.evaluate(occurrence, candles, records)) is not None
            ]
            if not outcomes:
                continue
            horizon_outcomes = [
                horizon
                for outcome in outcomes
                for horizon in outcome.horizons
                if horizon.horizon == 20
            ]
            if not horizon_outcomes:
                continue
            mfe = [item.mfe_atr for item in horizon_outcomes]
            mae = [item.mae_atr for item in horizon_outcomes]
            returns = [item.return_atr for item in horizon_outcomes]
            split_performance = {
                split: self._split_mean(outcomes, split, horizon=20)
                for split in ("DISCOVERY", "VALIDATION", "OOS")
            }
            fp1 = self._first_passage_rate(outcomes, 1.0)
            fp2 = self._first_passage_rate(outcomes, 2.0)
            fp1_expectancy = self._first_passage_expectancy(outcomes, 1.0)
            fp2_expectancy = self._first_passage_expectancy(outcomes, 2.0)
            fp1_splits = {
                split: self._first_passage_expectancy(outcomes, 1.0, split=split)
                for split in ("DISCOVERY", "VALIDATION", "OOS")
            }
            fp2_splits = {
                split: self._first_passage_expectancy(outcomes, 2.0, split=split)
                for split in ("DISCOVERY", "VALIDATION", "OOS")
            }
            expectancy = mean(returns)
            score = self._score(
                len(outcomes),
                fp1_splits,
                fp2_splits,
            )
            rankings.append(
                PatternRanking(
                    pattern_id=key.pattern_id,
                    sequence=key.sequence,
                    gap_buckets=key.gaps,
                    direction=key.direction,
                    occurrences=len(outcomes),
                    frequency=len(outcomes) / max(len(records), 1),
                    mfe_mean_atr=mean(mfe),
                    mfe_median_atr=median(mfe),
                    mae_mean_atr=mean(mae),
                    mae_median_atr=median(mae),
                    return_mean_atr=mean(returns),
                    return_median_atr=median(returns),
                    first_passage_1_atr=fp1,
                    first_passage_2_atr=fp2,
                    expectancy=expectancy,
                    discovery_performance=split_performance["DISCOVERY"],
                    validation_performance=split_performance["VALIDATION"],
                    oos_performance=split_performance["OOS"],
                    score=score,
                    first_passage_1_expectancy_net=fp1_expectancy,
                    first_passage_2_expectancy_net=fp2_expectancy,
                    fp1_discovery_net=fp1_splits["DISCOVERY"],
                    fp1_validation_net=fp1_splits["VALIDATION"],
                    fp1_oos_net=fp1_splits["OOS"],
                    fp2_discovery_net=fp2_splits["DISCOVERY"],
                    fp2_validation_net=fp2_splits["VALIDATION"],
                    fp2_oos_net=fp2_splits["OOS"],
                )
            )
        rankings.sort(key=lambda ranking: (-ranking.score, -ranking.occurrences, ranking.pattern_id))
        return rankings

    @staticmethod
    def _split_mean(
        outcomes: list[OccurrenceOutcome],
        split: str,
        *,
        horizon: int,
    ) -> float:
        values = [
            item.return_atr
            for outcome in outcomes
            if outcome.occurrence.split == split
            for item in outcome.horizons
            if item.horizon == horizon
        ]
        return mean(values) if values else 0.0

    @staticmethod
    def _first_passage_rate(
        outcomes: list[OccurrenceOutcome],
        target: float,
    ) -> float:
        statuses = [
            item.status
            for outcome in outcomes
            for item in outcome.first_passage
            if math.isclose(item.target_atr, target)
        ]
        resolved = [status for status in statuses if status in {"SUCCESS", "FAILURE"}]
        if not resolved:
            return 0.0
        return sum(status == "SUCCESS" for status in resolved) / len(resolved)

    def _first_passage_expectancy(
        self,
        outcomes: list[OccurrenceOutcome],
        target: float,
        *,
        split: str | None = None,
    ) -> float:
        values: list[float] = []
        for outcome in outcomes:
            if split is not None and outcome.occurrence.split != split:
                continue
            result = next(
                (
                    item
                    for item in outcome.first_passage
                    if math.isclose(item.target_atr, target)
                ),
                None,
            )
            if result is None or result.status == "UNRESOLVED":
                continue
            gross_r = target if result.status == "SUCCESS" else -1.0
            values.append(gross_r - self.config.execution_friction_r)
        return mean(values) if values else 0.0

    def _score(
        self,
        sample_size: int,
        fp1_splits: dict[str, float],
        fp2_splits: dict[str, float],
    ) -> float:
        sample_penalty = min(
            1.0,
            math.sqrt(
                sample_size / max(self.config.operational_min_occurrences, 1)
            ),
        )

        def robust_score(values: dict[str, float]) -> float:
            discovery = values["DISCOVERY"]
            validation = values["VALIDATION"]
            oos = values["OOS"]
            floor = min(discovery, validation, oos)
            instability = abs(discovery - validation) + abs(discovery - oos)
            return floor * sample_penalty - 0.15 * instability

        return max(robust_score(fp1_splits), robust_score(fp2_splits))

    @staticmethod
    def _gap_bucket(gap: int) -> str:
        if gap == 0:
            return "same candle"
        if gap <= 2:
            return "1-2 candles"
        if gap <= 5:
            return "3-5 candles"
        return "6-12 candles"

    @staticmethod
    def _split(index: int, discovery_end: int, validation_end: int) -> str:
        if index < discovery_end:
            return "DISCOVERY"
        if index < validation_end:
            return "VALIDATION"
        return "OOS"
