"""Validador estrutural de candles de mercado."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from market.data.market_data_contract import MarketDataContract


@dataclass(frozen=True)
class CandleValidationResult:
    """Resultado da validacao estrutural de um candle."""

    is_valid: bool
    validation_messages: tuple[str, ...]


@dataclass(frozen=True)
class CandleValidator:
    """Valida apenas consistencia estrutural de dados de mercado."""

    def validate(self, candle: MarketDataContract) -> CandleValidationResult:
        """Retorna mensagens sobre o candle recebido."""
        messages: list[str] = []
        self._require_complete_candle(candle, messages)
        self._require_valid_timestamp(candle.timestamp, messages)
        self._require_numeric_values(candle, messages)
        self._require_consistent_ohlc(candle, messages)
        self._require_non_negative_volume(candle.volume, messages)
        return CandleValidationResult(
            is_valid=not messages,
            validation_messages=tuple(messages),
        )

    def _require_complete_candle(
        self,
        candle: MarketDataContract,
        messages: list[str],
    ) -> None:
        if not candle.symbol.strip():
            messages.append("Simbolo do candle nao definido.")
        if not candle.timeframe.strip():
            messages.append("Timeframe do candle nao definido.")
        if not candle.timestamp.strip():
            messages.append("Timestamp do candle nao definido.")

    def _require_valid_timestamp(self, timestamp: str, messages: list[str]) -> None:
        if not timestamp.strip():
            return
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            messages.append("Timestamp do candle invalido.")

    def _require_numeric_values(
        self,
        candle: MarketDataContract,
        messages: list[str],
    ) -> None:
        values = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )
        if not all(isfinite(value) for value in values):
            messages.append("Valores numericos do candle invalidos.")

    def _require_consistent_ohlc(
        self,
        candle: MarketDataContract,
        messages: list[str],
    ) -> None:
        if candle.high < candle.low:
            messages.append("OHLC inconsistente: high menor que low.")
        if candle.open > candle.high or candle.open < candle.low:
            messages.append("OHLC inconsistente: open fora do intervalo.")
        if candle.close > candle.high or candle.close < candle.low:
            messages.append("OHLC inconsistente: close fora do intervalo.")

    def _require_non_negative_volume(
        self,
        volume: float,
        messages: list[str],
    ) -> None:
        if volume < 0:
            messages.append("Volume do candle negativo.")
