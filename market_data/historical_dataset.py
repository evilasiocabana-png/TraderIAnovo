"""Representacao de datasets historicos de mercado."""

from dataclasses import dataclass, field

from domain.candle import Candle


@dataclass(frozen=True)
class HistoricalDataset:
    """Conjunto historico de candles normalizado."""

    symbol: str
    timeframe: str
    start_date: str | None
    end_date: str | None
    candles: list[Candle] = field(default_factory=list)

    @property
    def total_candles(self) -> int:
        """Retorna a quantidade de candles do dataset."""
        return len(self.candles)

    @property
    def is_empty(self) -> bool:
        """Indica se o dataset esta vazio."""
        return not self.candles
