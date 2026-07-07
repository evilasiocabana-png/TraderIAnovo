"""Analisador deterministico da estrutura de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from domain.candle import Candle
from market.structure.market_structure_snapshot import MarketStructureSnapshot


@dataclass(frozen=True)
class MarketStructureAnalyzer:
    """Calcula estrutura de mercado sem gerar decisao operacional."""

    donchian_period: int = 20
    bollinger_period: int = 20
    bollinger_deviation: float = 2.0
    z_score_period: int = 20
    tick_volume_period: int = 20
    fast_ema_period: int = 20
    medium_ema_period: int = 50
    slow_ema_period: int = 100
    short_volatility_period: int = 10
    long_volatility_period: int = 30
    range_period: int = 20
    swing_lookback: int = 2
    price_velocity_period: int = 5
    max_spread_to_average_ratio: float = 1.8

    def analyze(
        self,
        candles: list[Candle],
        symbol: str = "N/D",
        timeframe: str = "N/D",
        multi_timeframe_candles: dict[str, list[Candle]] | None = None,
        current_bid: float | None = None,
        current_ask: float | None = None,
        spread_history: list[float] | None = None,
        session: str = "N/D",
    ) -> MarketStructureSnapshot:
        """Retorna snapshot estrutural para a ultima vela disponivel."""
        ordered = list(candles)
        if not ordered:
            return self._empty_snapshot(symbol, timeframe)

        current = ordered[-1]
        current_price = float(current.fechamento)
        donchian_sample = ordered[-self._period(self.donchian_period) :]
        donchian_high = max(float(candle.maxima) for candle in donchian_sample)
        donchian_low = min(float(candle.minima) for candle in donchian_sample)
        donchian_mid = (donchian_high + donchian_low) / 2.0
        donchian_position = self._position(current_price, donchian_low, donchian_high)

        pivot_candle = ordered[-2] if len(ordered) >= 2 else current
        pivot = (
            float(pivot_candle.maxima)
            + float(pivot_candle.minima)
            + float(pivot_candle.fechamento)
        ) / 3.0
        pivot_r1 = (2.0 * pivot) - float(pivot_candle.minima)
        pivot_s1 = (2.0 * pivot) - float(pivot_candle.maxima)
        pivot_range = float(pivot_candle.maxima) - float(pivot_candle.minima)
        pivot_r2 = pivot + pivot_range
        pivot_s2 = pivot - pivot_range

        vwap = self._vwap(ordered)
        distance_to_vwap = self._relative_distance(current_price, vwap)

        z_score = self._z_score(
            [float(candle.fechamento) for candle in ordered[-self._period(self.z_score_period) :]]
        )

        bollinger_sample = [
            float(candle.fechamento)
            for candle in ordered[-self._period(self.bollinger_period) :]
        ]
        bollinger_middle = self._mean(bollinger_sample)
        bollinger_std = self._std(bollinger_sample)
        bollinger_upper = bollinger_middle + (self.bollinger_deviation * bollinger_std)
        bollinger_lower = bollinger_middle - (self.bollinger_deviation * bollinger_std)
        bollinger_width = bollinger_upper - bollinger_lower
        bollinger_position = self._position(
            current_price,
            bollinger_lower,
            bollinger_upper,
        )

        volume_sample = ordered[-self._period(self.tick_volume_period) :]
        tick_volume = int(current.volume)
        tick_volume_average = self._mean([float(candle.volume) for candle in volume_sample])
        relative_tick_volume = (
            tick_volume / tick_volume_average if tick_volume_average > 0.0 else 0.0
        )
        current_spread = self._current_spread(current_bid, current_ask)
        average_spread = self._average_spread(current_spread, spread_history)
        spread_to_average_ratio = (
            current_spread / average_spread if average_spread > 0.0 else 0.0
        )
        estimated_slippage = self._estimated_slippage(
            current_spread,
            average_spread,
            relative_tick_volume,
        )
        price_velocity = self._price_velocity(ordered, self.price_velocity_period)
        session_liquidity = self._session_liquidity(relative_tick_volume, session)
        spread_blocked = (
            average_spread > 0.0
            and spread_to_average_ratio >= self.max_spread_to_average_ratio
        )
        spread_status = "BLOCKED_HIGH_SPREAD" if spread_blocked else "OK"
        range_sample = ordered[-self._period(self.range_period) :]
        current_range_high = max(float(candle.maxima) for candle in range_sample)
        current_range_low = min(float(candle.minima) for candle in range_sample)
        current_range_size = current_range_high - current_range_low
        current_range_position = self._position(
            current_price,
            current_range_low,
            current_range_high,
        )
        support = current_range_low
        resistance = current_range_high
        swing_high = self._last_swing_high(range_sample)
        swing_low = self._last_swing_low(range_sample)
        relevant_high = max(donchian_high, current_range_high, swing_high)
        relevant_low = min(donchian_low, current_range_low, swing_low)
        range_breakout = self._range_breakout(
            current_price,
            current_range_high,
            current_range_low,
        )
        distance_to_support = self._relative_distance(current_price, support)
        distance_to_resistance = self._relative_distance(resistance, current_price)
        nearest_structure_level = self._nearest_level(
            current_price,
            (support, resistance, swing_high, swing_low, pivot, vwap),
        )
        distance_to_nearest_structure = self._relative_distance(
            current_price,
            nearest_structure_level,
        )
        fast_ema = self._ema(
            [float(candle.fechamento) for candle in ordered],
            self.fast_ema_period,
        )
        medium_ema = self._ema(
            [float(candle.fechamento) for candle in ordered],
            self.medium_ema_period,
        )
        slow_ema = self._ema(
            [float(candle.fechamento) for candle in ordered],
            self.slow_ema_period,
        )
        distance_to_fast_ema = self._relative_distance(current_price, fast_ema)
        distance_to_medium_ema = self._relative_distance(current_price, medium_ema)
        distance_to_slow_ema = self._relative_distance(current_price, slow_ema)
        atr_short = self._atr(ordered, self.short_volatility_period)
        atr_long = self._atr(ordered, self.long_volatility_period)
        volatility_ratio = atr_short / atr_long if atr_long > 0.0 else 1.0
        volatility_compression = max(0.0, min(1.0 - volatility_ratio, 1.0))
        volatility_expansion = max(0.0, min(volatility_ratio - 1.0, 1.0))
        trend_strength = self._trend_strength(
            ordered,
            fast_ema,
            medium_ema,
            slow_ema,
            atr_long,
        )
        current_timeframe_direction = self._direction(
            current_price,
            fast_ema,
            medium_ema,
            slow_ema,
        )
        timeframe_directions = self._timeframe_directions(
            ordered,
            timeframe,
            multi_timeframe_candles,
        )
        dominant_direction = self._dominant_direction(timeframe_directions)
        regime = self._regime(
            trend_strength,
            volatility_expansion,
            volatility_compression,
            dominant_direction,
        )

        return MarketStructureSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            candles_count=len(ordered),
            donchian_period=self.donchian_period,
            donchian_high=donchian_high,
            donchian_low=donchian_low,
            donchian_mid=donchian_mid,
            donchian_position=donchian_position,
            pivot=pivot,
            pivot_r1=pivot_r1,
            pivot_r2=pivot_r2,
            pivot_s1=pivot_s1,
            pivot_s2=pivot_s2,
            vwap=vwap,
            distance_to_vwap=distance_to_vwap,
            z_score=z_score,
            bollinger_period=self.bollinger_period,
            bollinger_upper=bollinger_upper,
            bollinger_middle=bollinger_middle,
            bollinger_lower=bollinger_lower,
            bollinger_width=bollinger_width,
            bollinger_position=bollinger_position,
            tick_volume=tick_volume,
            tick_volume_average=tick_volume_average,
            relative_tick_volume=relative_tick_volume,
            current_spread=current_spread,
            average_spread=average_spread,
            spread_to_average_ratio=spread_to_average_ratio,
            estimated_slippage=estimated_slippage,
            price_velocity=price_velocity,
            session=session,
            session_liquidity=session_liquidity,
            spread_blocked=spread_blocked,
            spread_status=spread_status,
            support=support,
            resistance=resistance,
            swing_high=swing_high,
            swing_low=swing_low,
            relevant_high=relevant_high,
            relevant_low=relevant_low,
            current_range_high=current_range_high,
            current_range_low=current_range_low,
            current_range_size=current_range_size,
            current_range_position=current_range_position,
            range_breakout=range_breakout,
            distance_to_support=distance_to_support,
            distance_to_resistance=distance_to_resistance,
            nearest_structure_level=nearest_structure_level,
            distance_to_nearest_structure=distance_to_nearest_structure,
            structure_status=self._structure_status(
                current_price,
                donchian_high,
                donchian_low,
                donchian_position,
                bollinger_position,
            ),
            regime=regime,
            trend_strength=trend_strength,
            volatility_compression=volatility_compression,
            volatility_expansion=volatility_expansion,
            fast_ema_period=self.fast_ema_period,
            medium_ema_period=self.medium_ema_period,
            slow_ema_period=self.slow_ema_period,
            fast_ema=fast_ema,
            medium_ema=medium_ema,
            slow_ema=slow_ema,
            distance_to_fast_ema=distance_to_fast_ema,
            distance_to_medium_ema=distance_to_medium_ema,
            distance_to_slow_ema=distance_to_slow_ema,
            current_timeframe_direction=current_timeframe_direction,
            dominant_multi_timeframe_direction=dominant_direction,
            timeframe_directions=timeframe_directions,
            confidence=self._confidence(
                len(ordered),
                donchian_position,
                bollinger_position,
                relative_tick_volume,
            ),
        )

    def _empty_snapshot(self, symbol: str, timeframe: str) -> MarketStructureSnapshot:
        return MarketStructureSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            current_price=0.0,
            candles_count=0,
            donchian_period=self.donchian_period,
            donchian_high=0.0,
            donchian_low=0.0,
            donchian_mid=0.0,
            donchian_position=0.0,
            pivot=0.0,
            pivot_r1=0.0,
            pivot_r2=0.0,
            pivot_s1=0.0,
            pivot_s2=0.0,
            vwap=0.0,
            distance_to_vwap=0.0,
            z_score=0.0,
            bollinger_period=self.bollinger_period,
            bollinger_upper=0.0,
            bollinger_middle=0.0,
            bollinger_lower=0.0,
            bollinger_width=0.0,
            bollinger_position=0.0,
            tick_volume=0,
            tick_volume_average=0.0,
            relative_tick_volume=0.0,
            current_spread=0.0,
            average_spread=0.0,
            spread_to_average_ratio=0.0,
            estimated_slippage=0.0,
            price_velocity=0.0,
            session="N/D",
            session_liquidity="UNKNOWN",
            spread_blocked=False,
            spread_status="NO_DATA",
            support=0.0,
            resistance=0.0,
            swing_high=0.0,
            swing_low=0.0,
            relevant_high=0.0,
            relevant_low=0.0,
            current_range_high=0.0,
            current_range_low=0.0,
            current_range_size=0.0,
            current_range_position=0.0,
            range_breakout="NO_DATA",
            distance_to_support=0.0,
            distance_to_resistance=0.0,
            nearest_structure_level=0.0,
            distance_to_nearest_structure=0.0,
            structure_status="NO_DATA",
            regime="RANGE",
            trend_strength=0.0,
            volatility_compression=0.0,
            volatility_expansion=0.0,
            fast_ema_period=self.fast_ema_period,
            medium_ema_period=self.medium_ema_period,
            slow_ema_period=self.slow_ema_period,
            fast_ema=0.0,
            medium_ema=0.0,
            slow_ema=0.0,
            distance_to_fast_ema=0.0,
            distance_to_medium_ema=0.0,
            distance_to_slow_ema=0.0,
            current_timeframe_direction="SIDEWAYS",
            dominant_multi_timeframe_direction="SIDEWAYS",
            timeframe_directions=(),
            confidence=0.0,
        )

    def _period(self, value: int) -> int:
        return max(1, int(value))

    def _position(self, value: float, lower: float, upper: float) -> float:
        width = upper - lower
        if width <= 0.0:
            return 0.5
        return max(0.0, min((value - lower) / width, 1.0))

    def _relative_distance(self, value: float, reference: float) -> float:
        if reference == 0.0:
            return 0.0
        return (value - reference) / reference

    def _current_spread(
        self,
        current_bid: float | None,
        current_ask: float | None,
    ) -> float:
        if current_bid is None or current_ask is None:
            return 0.0
        return max(0.0, float(current_ask) - float(current_bid))

    def _average_spread(
        self,
        current_spread: float,
        spread_history: list[float] | None,
    ) -> float:
        values = [
            max(0.0, float(value))
            for value in (spread_history or [])
            if value is not None
        ]
        if values:
            return self._mean(values)
        return current_spread

    def _estimated_slippage(
        self,
        current_spread: float,
        average_spread: float,
        relative_tick_volume: float,
    ) -> float:
        spread_reference = max(current_spread, average_spread)
        if spread_reference <= 0.0:
            return 0.0
        liquidity_penalty = 1.0
        if relative_tick_volume > 0.0:
            liquidity_penalty = max(0.5, min(2.0, 1.0 / relative_tick_volume))
        return spread_reference * liquidity_penalty

    def _price_velocity(self, candles: list[Candle], period: int) -> float:
        if len(candles) < 2:
            return 0.0
        lookback = min(self._period(period), len(candles) - 1)
        current_price = float(candles[-1].fechamento)
        previous_price = float(candles[-1 - lookback].fechamento)
        if previous_price == 0.0:
            return 0.0
        return abs(current_price - previous_price) / lookback / abs(previous_price)

    def _session_liquidity(self, relative_tick_volume: float, session: str) -> str:
        if session == "N/D" and relative_tick_volume <= 0.0:
            return "UNKNOWN"
        if relative_tick_volume >= 1.25:
            return "HIGH"
        if relative_tick_volume >= 0.75:
            return "NORMAL"
        return "LOW"

    def _last_swing_high(self, candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        lookback = self._period(self.swing_lookback)
        for index in range(len(candles) - lookback - 1, lookback - 1, -1):
            high = float(candles[index].maxima)
            left = candles[index - lookback : index]
            right = candles[index + 1 : index + lookback + 1]
            if all(high >= float(candle.maxima) for candle in left + right):
                return high
        return max(float(candle.maxima) for candle in candles)

    def _last_swing_low(self, candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        lookback = self._period(self.swing_lookback)
        for index in range(len(candles) - lookback - 1, lookback - 1, -1):
            low = float(candles[index].minima)
            left = candles[index - lookback : index]
            right = candles[index + 1 : index + lookback + 1]
            if all(low <= float(candle.minima) for candle in left + right):
                return low
        return min(float(candle.minima) for candle in candles)

    def _range_breakout(
        self,
        current_price: float,
        current_range_high: float,
        current_range_low: float,
    ) -> str:
        if current_price >= current_range_high:
            return "BREAKOUT_UP"
        if current_price <= current_range_low:
            return "BREAKOUT_DOWN"
        return "INSIDE_RANGE"

    def _nearest_level(self, current_price: float, levels: tuple[float, ...]) -> float:
        valid_levels = [level for level in levels if level > 0.0]
        if not valid_levels:
            return 0.0
        return min(valid_levels, key=lambda level: abs(current_price - level))

    def _vwap(self, candles: list[Candle]) -> float:
        weighted_total = 0.0
        volume_total = 0.0
        for candle in candles:
            typical_price = (
                float(candle.maxima)
                + float(candle.minima)
                + float(candle.fechamento)
            ) / 3.0
            volume = max(0.0, float(candle.volume))
            weighted_total += typical_price * volume
            volume_total += volume
        if volume_total <= 0.0:
            return self._mean([float(candle.fechamento) for candle in candles])
        return weighted_total / volume_total

    def _z_score(self, values: list[float]) -> float:
        if not values:
            return 0.0
        mean = self._mean(values)
        std = self._std(values)
        if std == 0.0:
            return 0.0
        return (values[-1] - mean) / std

    def _mean(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _std(self, values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = self._mean(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return sqrt(variance)

    def _ema(self, values: list[float], period: int) -> float:
        if not values:
            return 0.0
        alpha = 2.0 / (self._period(period) + 1.0)
        ema = values[0]
        for value in values[1:]:
            ema = (value * alpha) + (ema * (1.0 - alpha))
        return ema

    def _atr(self, candles: list[Candle], period: int) -> float:
        sample = candles[-self._period(period) :]
        if not sample:
            return 0.0
        true_ranges = []
        previous_close = float(sample[0].fechamento)
        for candle in sample:
            high = float(candle.maxima)
            low = float(candle.minima)
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
            previous_close = float(candle.fechamento)
        return self._mean(true_ranges)

    def _trend_strength(
        self,
        candles: list[Candle],
        fast_ema: float,
        medium_ema: float,
        slow_ema: float,
        atr_reference: float,
    ) -> float:
        if not candles:
            return 0.0
        current_price = float(candles[-1].fechamento)
        first_price = float(candles[0].fechamento)
        price_reference = abs(current_price) if current_price != 0.0 else 1.0
        ema_spread = (abs(fast_ema - medium_ema) + abs(medium_ema - slow_ema)) / 2.0
        slope = abs(current_price - first_price) / max(len(candles), 1)
        volatility_reference = max(atr_reference, price_reference * 0.001)
        raw_strength = ((ema_spread + slope) / volatility_reference) / 3.0
        return max(0.0, min(raw_strength, 1.0))

    def _direction(
        self,
        current_price: float,
        fast_ema: float,
        medium_ema: float,
        slow_ema: float,
    ) -> str:
        if current_price > fast_ema > medium_ema > slow_ema:
            return "UP"
        if current_price < fast_ema < medium_ema < slow_ema:
            return "DOWN"
        return "SIDEWAYS"

    def _timeframe_directions(
        self,
        current_candles: list[Candle],
        current_timeframe: str,
        multi_timeframe_candles: dict[str, list[Candle]] | None,
    ) -> tuple[str, ...]:
        sources = {current_timeframe: current_candles}
        if multi_timeframe_candles:
            sources.update(multi_timeframe_candles)
        directions = []
        for timeframe, candles in sorted(sources.items()):
            if not candles:
                directions.append(f"{timeframe}:SIDEWAYS")
                continue
            closes = [float(candle.fechamento) for candle in candles]
            current_price = closes[-1]
            fast_ema = self._ema(closes, self.fast_ema_period)
            medium_ema = self._ema(closes, self.medium_ema_period)
            slow_ema = self._ema(closes, self.slow_ema_period)
            directions.append(
                f"{timeframe}:{self._direction(current_price, fast_ema, medium_ema, slow_ema)}"
            )
        return tuple(directions)

    def _dominant_direction(self, timeframe_directions: tuple[str, ...]) -> str:
        counts = {"UP": 0, "DOWN": 0, "SIDEWAYS": 0}
        for item in timeframe_directions:
            direction = item.split(":", 1)[-1]
            if direction in counts:
                counts[direction] += 1
        dominant = max(counts, key=counts.get)
        tied = [direction for direction, total in counts.items() if total == counts[dominant]]
        if len(tied) > 1:
            return "SIDEWAYS"
        return dominant

    def _regime(
        self,
        trend_strength: float,
        volatility_expansion: float,
        volatility_compression: float,
        dominant_direction: str,
    ) -> str:
        if volatility_expansion >= 0.35 and trend_strength < 0.45:
            return "VOLATILE"
        if trend_strength >= 0.35 and dominant_direction in {"UP", "DOWN"}:
            return "TREND"
        if volatility_compression >= 0.20:
            return "RANGE"
        return "RANGE"

    def _structure_status(
        self,
        current_price: float,
        donchian_high: float,
        donchian_low: float,
        donchian_position: float,
        bollinger_position: float,
    ) -> str:
        if current_price >= donchian_high:
            return "BREAKOUT_UP"
        if current_price <= donchian_low:
            return "BREAKOUT_DOWN"
        if donchian_position >= 0.75 and bollinger_position >= 0.65:
            return "UPPER_RANGE"
        if donchian_position <= 0.25 and bollinger_position <= 0.35:
            return "LOWER_RANGE"
        if 0.40 <= donchian_position <= 0.60:
            return "MID_RANGE"
        return "NEUTRAL"

    def _confidence(
        self,
        candles_count: int,
        donchian_position: float,
        bollinger_position: float,
        relative_tick_volume: float,
    ) -> float:
        minimum_period = max(
            self.donchian_period,
            self.bollinger_period,
            self.z_score_period,
            self.tick_volume_period,
        )
        sample_score = min(candles_count / max(1, minimum_period), 1.0) * 0.50
        position_alignment = 1.0 - abs(donchian_position - bollinger_position)
        alignment_score = max(0.0, min(position_alignment, 1.0)) * 0.30
        volume_score = min(relative_tick_volume, 1.5) / 1.5 * 0.20
        return max(0.0, min(sample_score + alignment_score + volume_score, 1.0))
