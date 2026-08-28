"""Stateful causal market-event detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.models import (
    CandleBar,
    EventRecord,
    IndicatorFrame,
    MarketEvent,
)


@dataclass(slots=True)
class _Zone:
    zone_id: str
    direction: int
    created_index: int
    top: float
    bottom: float
    midpoint: float
    state: str = "OPEN"
    retested: bool = False
    mitigated: bool = False


@dataclass(slots=True)
class _Swing:
    origin_index: int
    confirmed_index: int
    price: float
    swing_type: str
    structure_label: str


class CausalEventDetector:
    """Detect events using only candles at or before the current index."""

    def __init__(self, config: PatternMinerConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        """Reset every piece of causal detector state."""

        self.last_swing_high: _Swing | None = None
        self.last_swing_low: _Swing | None = None
        self.last_high_label = ""
        self.last_low_label = ""
        self.structure_state = "neutral"
        self.broken_high_origins: set[int] = set()
        self.broken_low_origins: set[int] = set()
        self.fvg_zones: list[_Zone] = []
        self.order_blocks: list[_Zone] = []

    def process(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
    ) -> EventRecord:
        """Build one immutable event snapshot for the current candle."""

        bar = candles[index]
        events: list[MarketEvent] = []
        self._detect_threshold_events(index, candles, indicators, events)
        self._update_fvg_zones(index, bar, indicators, events)
        self._update_order_blocks(index, bar, indicators, events)
        self._detect_breaks_and_liquidity(index, candles, indicators, events)
        self._confirm_swing(index, candles, indicators, events)
        self._detect_fvg(index, candles, indicators, events)
        self._detect_displacement_and_order_block(
            index,
            candles,
            indicators,
            events,
        )
        return EventRecord(
            index=index,
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            spread=bar.spread,
            real_volume=bar.real_volume,
            ema9=indicators.ema9[index],
            ema20=indicators.ema20[index],
            ema50=indicators.ema50[index],
            ema200=indicators.ema200[index],
            rsi14=indicators.rsi14[index],
            atr14=indicators.atr14[index],
            adx14=indicators.adx14[index],
            plus_di14=indicators.plus_di14[index],
            minus_di14=indicators.minus_di14[index],
            volume_average=indicators.volume_average[index],
            volume_relative=indicators.volume_relative[index],
            volume_zscore=indicators.volume_zscore[index],
            volume_percentile=indicators.volume_percentile[index],
            trend_state=self._trend_state(index, indicators),
            structure_state=self.structure_state,
            warmup_complete=index >= self.config.warmup_candles - 1,
            session=self._session(bar.timestamp.hour),
            events=tuple(events),
        )

    def _detect_threshold_events(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        if index <= 0:
            return
        self._cross_event(index, indicators.ema9, indicators.ema20, "EMA9", "20", events)
        self._cross_event(index, indicators.ema20, indicators.ema50, "EMA20", "50", events)
        self._cross_event(index, indicators.ema50, indicators.ema200, "EMA50", "200", events)

        current_rsi = indicators.rsi14[index]
        previous_rsi = indicators.rsi14[index - 1]
        if current_rsi is not None and previous_rsi is not None:
            if previous_rsi <= 50.0 < current_rsi:
                events.append(self._event("RSI_CROSS_50_UP", index, direction=1, intensity=current_rsi - 50.0))
            if previous_rsi >= 50.0 > current_rsi:
                events.append(self._event("RSI_CROSS_50_DOWN", index, direction=-1, intensity=50.0 - current_rsi))
            if previous_rsi < 70.0 <= current_rsi:
                events.append(self._event("RSI_OVERBOUGHT", index, direction=-1, intensity=current_rsi - 70.0))
            if previous_rsi > 30.0 >= current_rsi:
                events.append(self._event("RSI_OVERSOLD", index, direction=1, intensity=30.0 - current_rsi))

        current_adx = indicators.adx14[index]
        previous_adx = indicators.adx14[index - 1]
        if (
            current_adx is not None
            and previous_adx is not None
            and previous_adx < self.config.adx_high_threshold <= current_adx
        ):
            direction = self._di_direction(index, indicators)
            events.append(self._event("ADX_HIGH", index, direction=direction, intensity=current_adx))

        self._ratio_cross_event(
            index,
            indicators.atr_relative,
            self.config.atr_expansion_ratio,
            "ATR_EXPANSION",
            events,
            upward=True,
        )
        self._ratio_cross_event(
            index,
            indicators.atr_relative,
            self.config.atr_compression_ratio,
            "ATR_COMPRESSION",
            events,
            upward=False,
        )
        self._ratio_cross_event(
            index,
            indicators.volume_relative,
            self.config.volume_expansion_ratio,
            "VOLUME_EXPANSION",
            events,
            upward=True,
            direction=1 if candles[index].close >= candles[index].open else -1,
        )

    def _cross_event(
        self,
        index: int,
        first: list[float | None],
        second: list[float | None],
        first_name: str,
        second_name: str,
        events: list[MarketEvent],
    ) -> None:
        current_first = first[index]
        current_second = second[index]
        previous_first = first[index - 1]
        previous_second = second[index - 1]
        if None in (current_first, current_second, previous_first, previous_second):
            return
        assert current_first is not None and current_second is not None
        assert previous_first is not None and previous_second is not None
        if previous_first <= previous_second and current_first > current_second:
            events.append(
                self._event(
                    f"{first_name}_ABOVE_{second_name}",
                    index,
                    direction=1,
                    intensity=current_first - current_second,
                )
            )
        elif previous_first >= previous_second and current_first < current_second:
            events.append(
                self._event(
                    f"{first_name}_BELOW_{second_name}",
                    index,
                    direction=-1,
                    intensity=current_second - current_first,
                )
            )

    def _ratio_cross_event(
        self,
        index: int,
        values: list[float | None],
        threshold: float,
        event_type: str,
        events: list[MarketEvent],
        *,
        upward: bool,
        direction: int = 0,
    ) -> None:
        current = values[index]
        previous = values[index - 1]
        if current is None or previous is None:
            return
        crossed = previous < threshold <= current if upward else previous > threshold >= current
        if crossed:
            events.append(self._event(event_type, index, direction=direction, intensity=current))

    def _detect_breaks_and_liquidity(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        if index <= 0:
            return
        bar = candles[index]
        previous = candles[index - 1]
        atr = indicators.atr14[index]
        if self.last_swing_high is not None:
            swing = self.last_swing_high
            level = swing.price
            if bar.high > level and bar.close <= level:
                penetration = bar.high - level
                wick = bar.high - max(bar.open, bar.close)
                events.append(
                    self._event(
                        "SWEEP_HIGH",
                        index,
                        origin_index=swing.origin_index,
                        direction=-1,
                        level=level,
                        intensity=self._safe_ratio(penetration, atr),
                        penetration_points=penetration,
                        penetration_atr=self._safe_ratio(penetration, atr),
                        wick_size=wick,
                        wick_ratio=self._safe_ratio(wick, bar.high - bar.low),
                        close_relative_to_level=bar.close - level,
                        candles_since_liquidity=index - swing.confirmed_index,
                    )
                )
            if (
                swing.origin_index not in self.broken_high_origins
                and previous.close <= level < bar.close
            ):
                prior_structure = self.structure_state
                event_type = "CHOCH_UP" if prior_structure == "bearish" else "BOS_UP"
                distance = bar.close - level
                events.append(
                    self._event(
                        event_type,
                        index,
                        origin_index=swing.origin_index,
                        direction=1,
                        level=level,
                        intensity=self._safe_ratio(distance, atr),
                        break_price=bar.close,
                        distance_points=distance,
                        distance_atr=self._safe_ratio(distance, atr),
                        prior_structure=prior_structure,
                    )
                )
                self.broken_high_origins.add(swing.origin_index)
        if self.last_swing_low is not None:
            swing = self.last_swing_low
            level = swing.price
            if bar.low < level and bar.close >= level:
                penetration = level - bar.low
                wick = min(bar.open, bar.close) - bar.low
                events.append(
                    self._event(
                        "SWEEP_LOW",
                        index,
                        origin_index=swing.origin_index,
                        direction=1,
                        level=level,
                        intensity=self._safe_ratio(penetration, atr),
                        penetration_points=penetration,
                        penetration_atr=self._safe_ratio(penetration, atr),
                        wick_size=wick,
                        wick_ratio=self._safe_ratio(wick, bar.high - bar.low),
                        close_relative_to_level=bar.close - level,
                        candles_since_liquidity=index - swing.confirmed_index,
                    )
                )
            if (
                swing.origin_index not in self.broken_low_origins
                and previous.close >= level > bar.close
            ):
                prior_structure = self.structure_state
                event_type = "CHOCH_DOWN" if prior_structure == "bullish" else "BOS_DOWN"
                distance = level - bar.close
                events.append(
                    self._event(
                        event_type,
                        index,
                        origin_index=swing.origin_index,
                        direction=-1,
                        level=level,
                        intensity=self._safe_ratio(distance, atr),
                        break_price=bar.close,
                        distance_points=distance,
                        distance_atr=self._safe_ratio(distance, atr),
                        prior_structure=prior_structure,
                    )
                )
                self.broken_low_origins.add(swing.origin_index)

    def _confirm_swing(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        left = self.config.swing_left
        right = self.config.swing_right
        origin = index - right
        if origin < left or index < left + right:
            return
        candidate = candles[origin]
        peers = candles[origin - left : origin] + candles[origin + 1 : index + 1]
        atr = indicators.atr14[index]
        if all(candidate.high > item.high for item in peers):
            previous = self.last_swing_high
            label = "HH" if previous is None or candidate.high > previous.price else "LH"
            swing = _Swing(origin, index, candidate.high, "HIGH", label)
            events.append(
                self._event(
                    "SWING_HIGH",
                    index,
                    origin_index=origin,
                    direction=0,
                    level=candidate.high,
                    confirmed_index=index,
                )
            )
            events.append(self._event(label, index, origin_index=origin, direction=1 if label == "HH" else -1, level=candidate.high))
            if previous is not None and abs(candidate.high - previous.price) <= self._tolerance(atr):
                events.append(
                    self._event(
                        "EQUAL_HIGHS",
                        index,
                        origin_index=origin,
                        direction=-1,
                        level=candidate.high,
                        intensity=self._safe_ratio(abs(candidate.high - previous.price), atr),
                        previous_origin_index=previous.origin_index,
                    )
                )
            self.last_swing_high = swing
            self.last_high_label = label
        if all(candidate.low < item.low for item in peers):
            previous = self.last_swing_low
            label = "HL" if previous is None or candidate.low > previous.price else "LL"
            swing = _Swing(origin, index, candidate.low, "LOW", label)
            events.append(
                self._event(
                    "SWING_LOW",
                    index,
                    origin_index=origin,
                    direction=0,
                    level=candidate.low,
                    confirmed_index=index,
                )
            )
            events.append(self._event(label, index, origin_index=origin, direction=1 if label == "HL" else -1, level=candidate.low))
            if previous is not None and abs(candidate.low - previous.price) <= self._tolerance(atr):
                events.append(
                    self._event(
                        "EQUAL_LOWS",
                        index,
                        origin_index=origin,
                        direction=1,
                        level=candidate.low,
                        intensity=self._safe_ratio(abs(candidate.low - previous.price), atr),
                        previous_origin_index=previous.origin_index,
                    )
                )
            self.last_swing_low = swing
            self.last_low_label = label
        if self.last_high_label == "HH" and self.last_low_label == "HL":
            self.structure_state = "bullish"
        elif self.last_high_label == "LH" and self.last_low_label == "LL":
            self.structure_state = "bearish"
        else:
            self.structure_state = "neutral"

    def _detect_fvg(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        if index < 2:
            return
        first = candles[index - 2]
        third = candles[index]
        atr = indicators.atr14[index]
        if third.low > first.high:
            bottom = first.high
            top = third.low
            self._create_fvg(index, 1, top, bottom, atr, events)
        elif third.high < first.low:
            bottom = third.high
            top = first.low
            self._create_fvg(index, -1, top, bottom, atr, events)

    def _create_fvg(
        self,
        index: int,
        direction: int,
        top: float,
        bottom: float,
        atr: float | None,
        events: list[MarketEvent],
    ) -> None:
        midpoint = (top + bottom) / 2.0
        zone = _Zone(f"FVG-{index}-{direction}", direction, index, top, bottom, midpoint)
        self.fvg_zones.append(zone)
        size = top - bottom
        events.append(
            self._event(
                "FVG_UP" if direction > 0 else "FVG_DOWN",
                index,
                direction=direction,
                level=midpoint,
                intensity=self._safe_ratio(size, atr),
                top=top,
                bottom=bottom,
                midpoint=midpoint,
                size_points=size,
                size_atr=self._safe_ratio(size, atr),
                state="OPEN",
            )
        )

    def _update_fvg_zones(
        self,
        index: int,
        bar: CandleBar,
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        for zone in self.fvg_zones:
            if zone.created_index >= index or zone.state in {"FILLED", "INVALIDATED"}:
                continue
            touched = bar.low <= zone.top if zone.direction > 0 else bar.high >= zone.bottom
            if touched and not zone.retested:
                zone.retested = True
                events.append(self._zone_event("FVG_RETEST", index, zone))
            midpoint_touched = bar.low <= zone.midpoint if zone.direction > 0 else bar.high >= zone.midpoint
            if midpoint_touched and not zone.mitigated:
                zone.mitigated = True
                zone.state = "MITIGATED"
                events.append(self._zone_event("FVG_MITIGATION", index, zone))
            filled = bar.low <= zone.bottom if zone.direction > 0 else bar.high >= zone.top
            invalidated = bar.close < zone.bottom if zone.direction > 0 else bar.close > zone.top
            if filled:
                zone.state = "FILLED"
                events.append(self._zone_event("FVG_FILL", index, zone))
            elif invalidated:
                zone.state = "INVALIDATED"
                events.append(self._zone_event("FVG_INVALIDATED", index, zone))
            elif touched and zone.state == "OPEN":
                zone.state = "PARTIAL"
        if len(self.fvg_zones) > 500:
            self.fvg_zones = self.fvg_zones[-500:]

    def _detect_displacement_and_order_block(
        self,
        index: int,
        candles: list[CandleBar],
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        bar = candles[index]
        atr = indicators.atr14[index]
        volume_relative = indicators.volume_relative[index]
        if atr is None or atr <= 0.0 or volume_relative is None:
            return
        body = abs(bar.close - bar.open)
        candle_range = bar.high - bar.low
        body_ratio = self._safe_ratio(body, candle_range)
        direction = 1 if bar.close > bar.open else -1 if bar.close < bar.open else 0
        qualifies = (
            direction != 0
            and body / atr >= self.config.displacement_body_atr
            and candle_range / atr >= self.config.displacement_range_atr
            and body_ratio >= self.config.displacement_body_ratio
            and volume_relative >= self.config.displacement_volume_relative
        )
        if not qualifies:
            return
        event_type = "DISPLACEMENT_UP" if direction > 0 else "DISPLACEMENT_DOWN"
        close_location = (
            (bar.close - bar.low) / candle_range
            if candle_range > 0.0
            else 0.5
        )
        events.append(
            self._event(
                event_type,
                index,
                direction=direction,
                intensity=body / atr,
                body_points=body,
                candle_range=candle_range,
                body_atr=body / atr,
                range_atr=candle_range / atr,
                body_ratio=body_ratio,
                volume_relative=volume_relative,
                volume_zscore=indicators.volume_zscore[index],
                close_location=close_location,
            )
        )
        self._create_order_block(index, direction, candles, atr, events)

    def _create_order_block(
        self,
        index: int,
        direction: int,
        candles: list[CandleBar],
        atr: float,
        events: list[MarketEvent],
    ) -> None:
        start = max(0, index - self.config.order_block_lookback)
        opposite = None
        for candidate_index in range(index - 1, start - 1, -1):
            candidate = candles[candidate_index]
            if (direction > 0 and candidate.close < candidate.open) or (
                direction < 0 and candidate.close > candidate.open
            ):
                opposite = candidate
                break
        if opposite is None:
            return
        top = opposite.high
        bottom = opposite.low
        zone = _Zone(
            f"OB-{opposite.index}-{direction}",
            direction,
            index,
            top,
            bottom,
            (top + bottom) / 2.0,
        )
        self.order_blocks.append(zone)
        events.append(
            self._event(
                "ORDER_BLOCK_UP" if direction > 0 else "ORDER_BLOCK_DOWN",
                index,
                origin_index=opposite.index,
                direction=direction,
                level=zone.midpoint,
                intensity=self._safe_ratio(top - bottom, atr),
                top=top,
                bottom=bottom,
                midpoint=zone.midpoint,
                definition="last_opposite_candle_before_objective_displacement",
            )
        )

    def _update_order_blocks(
        self,
        index: int,
        bar: CandleBar,
        indicators: IndicatorFrame,
        events: list[MarketEvent],
    ) -> None:
        for zone in self.order_blocks:
            if zone.created_index >= index or zone.state in {"FILLED", "INVALIDATED"}:
                continue
            overlaps = bar.low <= zone.top and bar.high >= zone.bottom
            if overlaps and not zone.retested:
                zone.retested = True
                events.append(self._zone_event("OB_RETEST", index, zone))
            midpoint_touched = bar.low <= zone.midpoint <= bar.high
            if midpoint_touched and not zone.mitigated:
                zone.mitigated = True
                zone.state = "MITIGATED"
                events.append(self._zone_event("OB_MITIGATION", index, zone))
            invalidated = bar.close < zone.bottom if zone.direction > 0 else bar.close > zone.top
            if invalidated:
                zone.state = "INVALIDATED"
        if len(self.order_blocks) > 300:
            self.order_blocks = self.order_blocks[-300:]

    def _trend_state(self, index: int, indicators: IndicatorFrame) -> str:
        values = (
            indicators.ema9[index],
            indicators.ema20[index],
            indicators.ema50[index],
            indicators.ema200[index],
        )
        if any(value is None for value in values):
            return "warmup"
        ema9, ema20, ema50, ema200 = values
        assert ema9 is not None and ema20 is not None and ema50 is not None and ema200 is not None
        if ema9 > ema20 > ema50 > ema200:
            return "bullish"
        if ema9 < ema20 < ema50 < ema200:
            return "bearish"
        return "mixed"

    def _session(self, hour: int) -> str:
        if self.config.session_asia_start_utc <= hour < self.config.session_london_start_utc:
            return "Asia"
        if self.config.session_london_start_utc <= hour < self.config.session_new_york_start_utc:
            return "London"
        if self.config.session_new_york_start_utc <= hour < self.config.session_end_utc:
            return "New York"
        return "Off hours"

    def _di_direction(self, index: int, indicators: IndicatorFrame) -> int:
        plus_di = indicators.plus_di14[index]
        minus_di = indicators.minus_di14[index]
        if plus_di is None or minus_di is None:
            return 0
        return 1 if plus_di > minus_di else -1 if minus_di > plus_di else 0

    def _tolerance(self, atr: float | None) -> float:
        return max((atr or 0.0) * self.config.equal_level_tolerance_atr, 1e-9)

    @staticmethod
    def _safe_ratio(value: float, denominator: float | None) -> float:
        return value / denominator if denominator is not None and denominator > 0.0 else 0.0

    def _event(
        self,
        event_type: str,
        index: int,
        *,
        origin_index: int | None = None,
        direction: int = 0,
        level: float | None = None,
        intensity: float | None = None,
        **features: Any,
    ) -> MarketEvent:
        return MarketEvent(
            event_type=event_type,
            index=index,
            origin_index=index if origin_index is None else origin_index,
            direction=direction,
            level=level,
            intensity=intensity,
            features=tuple(sorted(features.items())),
        )

    def _zone_event(self, event_type: str, index: int, zone: _Zone) -> MarketEvent:
        return self._event(
            event_type,
            index,
            origin_index=zone.created_index,
            direction=zone.direction,
            level=zone.midpoint,
            top=zone.top,
            bottom=zone.bottom,
            midpoint=zone.midpoint,
            state=zone.state,
            age_candles=index - zone.created_index,
            zone_id=zone.zone_id,
        )
