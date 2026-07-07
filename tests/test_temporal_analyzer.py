"""Testes do analisador temporal de mercado."""

import unittest

from domain.candle import Candle
from market.candle_history import CandleHistory
from market.temporal_analyzer import TemporalAnalysis, TemporalMarketAnalyzer


class TemporalMarketAnalyzerTest(unittest.TestCase):
    """Valida analise temporal sobre CandleHistory."""

    def test_analise_com_historico_vazio(self) -> None:
        """Garante retorno neutro sem candles."""
        analysis = TemporalMarketAnalyzer().analyze(CandleHistory())

        self.assertEqual(analysis.candles_count, 0)
        self.assertEqual(analysis.direction, "SIDEWAYS")

    def test_direction_up_e_momentum(self) -> None:
        """Garante direcao de alta e momentum positivo."""
        history = self._history([100, 105, 110])

        analysis = TemporalMarketAnalyzer().analyze(history)

        self.assertEqual(analysis.direction, "UP")
        self.assertEqual(analysis.momentum, 10)

    def test_direction_down(self) -> None:
        """Garante direcao de baixa."""
        history = self._history([110, 105, 100])

        analysis = TemporalMarketAnalyzer().analyze(history)

        self.assertEqual(analysis.direction, "DOWN")

    def test_direction_sideways(self) -> None:
        """Garante direcao lateral."""
        history = self._history([100, 105, 100])

        analysis = TemporalMarketAnalyzer().analyze(history)

        self.assertEqual(analysis.direction, "SIDEWAYS")

    def test_calcula_metricas_temporais(self) -> None:
        """Garante range medio, maxima e minima."""
        history = CandleHistory()
        history.add_candle(self._candle(100, 110, 90))
        history.add_candle(self._candle(105, 120, 95))

        analysis = TemporalMarketAnalyzer().analyze(history)

        self.assertIsInstance(analysis, TemporalAnalysis)
        self.assertEqual(analysis.candles_count, 2)
        self.assertEqual(analysis.average_range, 22.5)
        self.assertEqual(analysis.highest_high, 120)
        self.assertEqual(analysis.lowest_low, 90)

    def _history(self, closes: list[float]) -> CandleHistory:
        history = CandleHistory()
        for close in closes:
            history.add_candle(self._candle(close, close + 5, close - 5))
        return history

    def _candle(self, close: float, high: float, low: float) -> Candle:
        return Candle(
            data="2026-06-26 09:00",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=1000,
        )


if __name__ == "__main__":
    unittest.main()
