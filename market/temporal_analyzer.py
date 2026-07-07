"""Analisador temporal baseado em historico de candles."""

from dataclasses import dataclass

from domain.candle import Candle
from market.candle_history import CandleHistory


@dataclass(frozen=True)
class TemporalAnalysis:
    """Resumo temporal de uma janela de candles."""

    candles_count: int
    direction: str
    momentum: float
    average_range: float
    highest_high: float | None
    lowest_low: float | None


@dataclass(frozen=True)
class TemporalMarketAnalyzer:
    """Extrai informacoes simples de uma sequencia recente de candles."""

    def analyze(self, candle_history: CandleHistory) -> TemporalAnalysis:
        """Analisa todos os candles disponiveis no historico."""
        candles = candle_history.last_n(candle_history.count())
        if not candles:
            return self._empty_analysis()

        first_close = candles[0].fechamento
        last_close = candles[-1].fechamento
        momentum = last_close - first_close

        return TemporalAnalysis(
            candles_count=len(candles),
            direction=self._direction(momentum),
            momentum=momentum,
            average_range=self._average_range(candles),
            highest_high=max(candle.maxima for candle in candles),
            lowest_low=min(candle.minima for candle in candles),
        )

    def _direction(self, momentum: float) -> str:
        if momentum > 0:
            return "UP"
        if momentum < 0:
            return "DOWN"
        return "SIDEWAYS"

    def _average_range(self, candles: list[Candle]) -> float:
        total_range = sum(candle.maxima - candle.minima for candle in candles)
        return total_range / len(candles)

    def _empty_analysis(self) -> TemporalAnalysis:
        return TemporalAnalysis(
            candles_count=0,
            direction="SIDEWAYS",
            momentum=0.0,
            average_range=0.0,
            highest_high=None,
            lowest_low=None,
        )
