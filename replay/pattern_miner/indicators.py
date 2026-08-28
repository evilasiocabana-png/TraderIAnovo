"""Causal indicator calculations for the XAUUSD replay."""

from __future__ import annotations

from collections import deque
import math

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.models import CandleBar, IndicatorFrame


class IndicatorEngine:
    """Calculate indicators using only values available at each candle."""

    def __init__(self, config: PatternMinerConfig) -> None:
        self.config = config

    def compute(self, candles: list[CandleBar]) -> IndicatorFrame:
        """Return a columnar causal indicator frame."""

        closes = [bar.close for bar in candles]
        highs = [bar.high for bar in candles]
        lows = [bar.low for bar in candles]
        volumes = [bar.volume for bar in candles]
        ema = {period: self._ema(closes, period) for period in self.config.ema_periods}
        rsi = self._rsi(closes, self.config.rsi_period)
        atr, plus_di, minus_di, adx = self._atr_adx(
            highs,
            lows,
            closes,
            self.config.atr_period,
        )
        if self.config.adx_period != self.config.atr_period:
            _, plus_di, minus_di, adx = self._atr_adx(
                highs,
                lows,
                closes,
                self.config.adx_period,
            )
        volume_average, volume_relative, volume_zscore, volume_percentile = (
            self._rolling_volume(volumes, self.config.volume_window)
        )
        atr_average = self._rolling_mean_optional(atr, self.config.volume_window)
        atr_relative = [
            self._ratio(value, average)
            for value, average in zip(atr, atr_average)
        ]
        return IndicatorFrame(
            ema9=ema[9],
            ema20=ema[20],
            ema50=ema[50],
            ema200=ema[200],
            rsi14=rsi,
            atr14=atr,
            adx14=adx,
            plus_di14=plus_di,
            minus_di14=minus_di,
            volume_average=volume_average,
            volume_relative=volume_relative,
            volume_zscore=volume_zscore,
            volume_percentile=volume_percentile,
            atr_relative=atr_relative,
        )

    @staticmethod
    def _ema(values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        if period <= 0 or len(values) < period:
            return result
        seed = sum(values[:period]) / period
        result[period - 1] = seed
        alpha = 2.0 / (period + 1.0)
        current = seed
        for index in range(period, len(values)):
            current = alpha * values[index] + (1.0 - alpha) * current
            result[index] = current
        return result

    @staticmethod
    def _rsi(closes: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        if period <= 0 or len(closes) <= period:
            return result
        gains = [0.0] * len(closes)
        losses = [0.0] * len(closes)
        for index in range(1, len(closes)):
            change = closes[index] - closes[index - 1]
            gains[index] = max(change, 0.0)
            losses[index] = max(-change, 0.0)
        average_gain = sum(gains[1 : period + 1]) / period
        average_loss = sum(losses[1 : period + 1]) / period
        result[period] = IndicatorEngine._rsi_value(average_gain, average_loss)
        for index in range(period + 1, len(closes)):
            average_gain = ((period - 1) * average_gain + gains[index]) / period
            average_loss = ((period - 1) * average_loss + losses[index]) / period
            result[index] = IndicatorEngine._rsi_value(average_gain, average_loss)
        return result

    @staticmethod
    def _rsi_value(average_gain: float, average_loss: float) -> float:
        if average_loss <= 0.0:
            return 100.0 if average_gain > 0.0 else 50.0
        relative_strength = average_gain / average_loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

    @staticmethod
    def _atr_adx(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int,
    ) -> tuple[
        list[float | None],
        list[float | None],
        list[float | None],
        list[float | None],
    ]:
        size = len(closes)
        atr: list[float | None] = [None] * size
        plus_di: list[float | None] = [None] * size
        minus_di: list[float | None] = [None] * size
        adx: list[float | None] = [None] * size
        if size <= period:
            return atr, plus_di, minus_di, adx

        true_ranges = [0.0] * size
        plus_dm = [0.0] * size
        minus_dm = [0.0] * size
        true_ranges[0] = highs[0] - lows[0]
        for index in range(1, size):
            true_ranges[index] = max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
            upward = highs[index] - highs[index - 1]
            downward = lows[index - 1] - lows[index]
            plus_dm[index] = upward if upward > downward and upward > 0.0 else 0.0
            minus_dm[index] = downward if downward > upward and downward > 0.0 else 0.0

        smoothed_tr = sum(true_ranges[1 : period + 1])
        smoothed_plus = sum(plus_dm[1 : period + 1])
        smoothed_minus = sum(minus_dm[1 : period + 1])
        dx: list[float | None] = [None] * size
        for index in range(period, size):
            if index > period:
                smoothed_tr = smoothed_tr - smoothed_tr / period + true_ranges[index]
                smoothed_plus = smoothed_plus - smoothed_plus / period + plus_dm[index]
                smoothed_minus = smoothed_minus - smoothed_minus / period + minus_dm[index]
            atr[index] = smoothed_tr / period
            if smoothed_tr <= 0.0:
                plus_di[index] = 0.0
                minus_di[index] = 0.0
                dx[index] = 0.0
                continue
            plus_di[index] = 100.0 * smoothed_plus / smoothed_tr
            minus_di[index] = 100.0 * smoothed_minus / smoothed_tr
            denominator = plus_di[index] + minus_di[index]
            dx[index] = (
                100.0 * abs(plus_di[index] - minus_di[index]) / denominator
                if denominator > 0.0
                else 0.0
            )

        first_adx_index = period * 2 - 1
        if size > first_adx_index:
            seed_values = [
                value
                for value in dx[period : first_adx_index + 1]
                if value is not None
            ]
            if len(seed_values) == period:
                current_adx = sum(seed_values) / period
                adx[first_adx_index] = current_adx
                for index in range(first_adx_index + 1, size):
                    current_dx = dx[index] if dx[index] is not None else current_adx
                    current_adx = ((period - 1) * current_adx + current_dx) / period
                    adx[index] = current_adx
        return atr, plus_di, minus_di, adx

    @staticmethod
    def _rolling_volume(
        volumes: list[float],
        window: int,
    ) -> tuple[
        list[float | None],
        list[float | None],
        list[float | None],
        list[float | None],
    ]:
        average: list[float | None] = [None] * len(volumes)
        relative: list[float | None] = [None] * len(volumes)
        zscore: list[float | None] = [None] * len(volumes)
        percentile: list[float | None] = [None] * len(volumes)
        rolling: deque[float] = deque()
        rolling_sum = 0.0
        rolling_square_sum = 0.0
        for index, value in enumerate(volumes):
            rolling.append(value)
            rolling_sum += value
            rolling_square_sum += value * value
            if len(rolling) > window:
                removed = rolling.popleft()
                rolling_sum -= removed
                rolling_square_sum -= removed * removed
            if len(rolling) < window:
                continue
            mean = rolling_sum / window
            variance = max(rolling_square_sum / window - mean * mean, 0.0)
            standard_deviation = math.sqrt(variance)
            average[index] = mean
            relative[index] = value / mean if mean > 0.0 else None
            zscore[index] = (value - mean) / standard_deviation if standard_deviation > 0.0 else 0.0
            below_or_equal = sum(1 for item in rolling if item <= value)
            percentile[index] = 100.0 * below_or_equal / window
        return average, relative, zscore, percentile

    @staticmethod
    def _rolling_mean_optional(
        values: list[float | None],
        window: int,
    ) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        rolling: deque[float] = deque()
        rolling_sum = 0.0
        for index, value in enumerate(values):
            if value is None:
                rolling.clear()
                rolling_sum = 0.0
                continue
            rolling.append(value)
            rolling_sum += value
            if len(rolling) > window:
                rolling_sum -= rolling.popleft()
            if len(rolling) == window:
                result[index] = rolling_sum / window
        return result

    @staticmethod
    def _ratio(value: float | None, denominator: float | None) -> float | None:
        if value is None or denominator is None or denominator <= 0.0:
            return None
        return value / denominator
