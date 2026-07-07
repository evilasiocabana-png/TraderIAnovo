"""Motor de calculo da Opening Range da Alpha 001 IORB."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Sequence


@dataclass(frozen=True)
class OpeningRange:
    """Faixa inicial calculada a partir dos candles de abertura."""

    start_time: str
    end_time: str
    high: float | None
    low: float | None
    range_size: float
    is_complete: bool


@dataclass
class OpeningRangeEngine:
    """Calcula Opening Range sem gerar sinais ou ordens."""

    current_range: OpeningRange | None = None

    def build(
        self,
        candles: Sequence[Any],
        start_time: str = "09:00",
        end_time: str = "09:15",
    ) -> OpeningRange:
        """Calcula a faixa inicial usando candles dentro do intervalo."""
        selected = [
            candle
            for candle in candles
            if self._is_inside_range(candle, start_time, end_time)
        ]

        if not selected:
            self.current_range = self._empty_range(start_time, end_time)
            return self.current_range

        high = max(float(candle.maxima) for candle in selected)
        low = min(float(candle.minima) for candle in selected)
        self.current_range = OpeningRange(
            start_time=start_time,
            end_time=end_time,
            high=high,
            low=low,
            range_size=high - low,
            is_complete=True,
        )
        return self.current_range

    def is_breakout_up(self, price: float) -> bool:
        """Indica rompimento acima da maxima da Opening Range."""
        if self.current_range is None or self.current_range.high is None:
            return False
        if not self.current_range.is_complete:
            return False
        return price > self.current_range.high

    def is_breakout_down(self, price: float) -> bool:
        """Indica rompimento abaixo da minima da Opening Range."""
        if self.current_range is None or self.current_range.low is None:
            return False
        if not self.current_range.is_complete:
            return False
        return price < self.current_range.low

    def _is_inside_range(
        self,
        candle: Any,
        start_time: str,
        end_time: str,
    ) -> bool:
        candle_time = self._extract_time(getattr(candle, "data", ""))
        return self._parse_time(start_time) <= candle_time <= self._parse_time(end_time)

    def _extract_time(self, value: Any) -> time:
        if hasattr(value, "time"):
            return value.time()
        time_text = str(value).strip().split()[-1]
        return self._parse_time(time_text[:5])

    def _parse_time(self, value: str) -> time:
        hour, minute = value.split(":")
        return time(hour=int(hour), minute=int(minute))

    def end_time_from_duration(
        self,
        start_time: str,
        duration_minutes: int,
    ) -> str:
        """Calcula horario final a partir do inicio e duracao configurados."""
        start = datetime.strptime(start_time, "%H:%M")
        return (start + timedelta(minutes=duration_minutes)).strftime("%H:%M")

    def _empty_range(self, start_time: str, end_time: str) -> OpeningRange:
        return OpeningRange(
            start_time=start_time,
            end_time=end_time,
            high=None,
            low=None,
            range_size=0.0,
            is_complete=False,
        )
