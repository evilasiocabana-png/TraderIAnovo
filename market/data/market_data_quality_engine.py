"""Avaliador de qualidade de dados de mercado."""

from dataclasses import dataclass
from datetime import datetime

from market.data.market_data_contract import MarketDataContract


@dataclass(frozen=True)
class MarketDataQualityResult:
    """Resultado consolidado de qualidade dos dados de mercado."""

    total_candles: int
    valid_candles: int
    invalid_candles: int
    missing_candles: int
    duplicated_candles: int
    quality_score: float


@dataclass(frozen=True)
class MarketDataQualityEngine:
    """Calcula apenas indicadores de qualidade dos candles recebidos."""

    def evaluate(
        self,
        candles: tuple[MarketDataContract, ...],
    ) -> MarketDataQualityResult:
        """Retorna estatisticas de qualidade sem modificar os dados."""
        total_candles = len(candles)
        valid_candles = len([candle for candle in candles if candle.is_valid])
        invalid_candles = total_candles - valid_candles
        duplicated_candles = self._duplicated_candles(candles)
        missing_candles = self._missing_candles(candles)
        quality_score = self._quality_score(
            valid_candles,
            duplicated_candles,
            total_candles,
            missing_candles,
        )
        return MarketDataQualityResult(
            total_candles=total_candles,
            valid_candles=valid_candles,
            invalid_candles=invalid_candles,
            missing_candles=missing_candles,
            duplicated_candles=duplicated_candles,
            quality_score=quality_score,
        )

    def _duplicated_candles(
        self,
        candles: tuple[MarketDataContract, ...],
    ) -> int:
        seen: set[tuple[str, str, str]] = set()
        duplicates = 0
        for candle in candles:
            key = (candle.symbol, candle.timeframe, candle.timestamp)
            if key in seen:
                duplicates += 1
            seen.add(key)
        return duplicates

    def _missing_candles(
        self,
        candles: tuple[MarketDataContract, ...],
    ) -> int:
        grouped: dict[tuple[str, str], list[datetime]] = {}
        for candle in candles:
            step_minutes = self._timeframe_minutes(candle.timeframe)
            if step_minutes is None:
                continue
            timestamp = self._parse_timestamp(candle.timestamp)
            if timestamp is None:
                continue
            key = (candle.symbol, candle.timeframe)
            grouped.setdefault(key, []).append(timestamp)

        missing = 0
        for key, timestamps in grouped.items():
            step_minutes = self._timeframe_minutes(key[1])
            if step_minutes is None:
                continue
            ordered = sorted(set(timestamps))
            for index in range(1, len(ordered)):
                delta_minutes = int(
                    (ordered[index] - ordered[index - 1]).total_seconds() / 60
                )
                if delta_minutes > step_minutes:
                    missing += (delta_minutes // step_minutes) - 1
        return missing

    def _quality_score(
        self,
        valid_candles: int,
        duplicated_candles: int,
        total_candles: int,
        missing_candles: int,
    ) -> float:
        expected_candles = total_candles + missing_candles
        if expected_candles == 0:
            return 0.0
        effective_valid = valid_candles - duplicated_candles
        if effective_valid < 0:
            effective_valid = 0
        return round((effective_valid / expected_candles) * 100, 2)

    def _timeframe_minutes(self, timeframe: str) -> int | None:
        if not timeframe.endswith("m"):
            return None
        value = timeframe[:-1]
        if not value.isdigit():
            return None
        minutes = int(value)
        if minutes < 1:
            return None
        return minutes

    def _parse_timestamp(self, timestamp: str) -> datetime | None:
        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            return None
