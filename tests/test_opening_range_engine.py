"""Testes do motor de Opening Range da Alpha 001."""

import unittest

from alpha.opening_range_engine import OpeningRange, OpeningRangeEngine
from domain.candle import Candle


class OpeningRangeEngineTest(unittest.TestCase):
    """Valida calculo isolado da faixa inicial."""

    def test_calcula_high_low_da_faixa(self) -> None:
        """Maior maxima e menor minima devem vir do intervalo."""
        opening_range = OpeningRangeEngine().build(self._candles())

        self.assertIsInstance(opening_range, OpeningRange)
        self.assertEqual(opening_range.high, 120.0)
        self.assertEqual(opening_range.low, 95.0)
        self.assertTrue(opening_range.is_complete)

    def test_calcula_range_size(self) -> None:
        """Range size deve ser high menos low."""
        opening_range = OpeningRangeEngine().build(self._candles())

        self.assertEqual(opening_range.range_size, 25.0)

    def test_detecta_breakout_para_cima(self) -> None:
        """Preco acima da maxima deve indicar breakout up."""
        engine = OpeningRangeEngine()
        engine.build(self._candles())

        self.assertTrue(engine.is_breakout_up(121.0))
        self.assertFalse(engine.is_breakout_up(120.0))

    def test_detecta_breakout_para_baixo(self) -> None:
        """Preco abaixo da minima deve indicar breakout down."""
        engine = OpeningRangeEngine()
        engine.build(self._candles())

        self.assertTrue(engine.is_breakout_down(94.0))
        self.assertFalse(engine.is_breakout_down(95.0))

    def test_retorna_incomplete_sem_candles_suficientes(self) -> None:
        """Sem candles no intervalo, a faixa deve ficar incompleta."""
        engine = OpeningRangeEngine()
        opening_range = engine.build([self._candle("09:30", 130.0, 120.0)])

        self.assertFalse(opening_range.is_complete)
        self.assertIsNone(opening_range.high)
        self.assertIsNone(opening_range.low)
        self.assertEqual(opening_range.range_size, 0.0)
        self.assertFalse(engine.is_breakout_up(140.0))
        self.assertFalse(engine.is_breakout_down(110.0))

    def _candles(self) -> list[Candle]:
        return [
            self._candle("08:59", 200.0, 10.0),
            self._candle("09:00", 110.0, 100.0),
            self._candle("09:05", 120.0, 98.0),
            self._candle("09:15", 115.0, 95.0),
            self._candle("09:16", 300.0, 50.0),
        ]

    def _candle(self, candle_time: str, high: float, low: float) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=100.0,
            maxima=high,
            minima=low,
            fechamento=105.0,
            volume=1000,
        )


if __name__ == "__main__":
    unittest.main()
