"""Testes do historico de candles em memoria."""

import unittest

from domain.candle import Candle
from market.candle_history import CandleHistory


class CandleHistoryTest(unittest.TestCase):
    """Valida armazenamento temporal de candles."""

    def test_adiciona_candles(self) -> None:
        """Garante inclusao de candles."""
        history = CandleHistory()

        history.add_candle(self._candle(1))

        self.assertEqual(history.count(), 1)

    def test_recupera_ultimo(self) -> None:
        """Garante retorno do ultimo candle."""
        history = CandleHistory()
        candle = self._candle(1)

        history.add_candle(candle)

        self.assertEqual(history.last(), candle)

    def test_recupera_anterior(self) -> None:
        """Garante retorno do candle anterior."""
        history = CandleHistory()
        previous = self._candle(1)
        latest = self._candle(2)

        history.add_candle(previous)
        history.add_candle(latest)

        self.assertEqual(history.previous(), previous)

    def test_recupera_ultimos_n(self) -> None:
        """Garante retorno dos ultimos N candles."""
        history = CandleHistory()
        candles = [self._candle(index) for index in range(4)]

        for candle in candles:
            history.add_candle(candle)

        self.assertEqual(history.last_n(2), candles[-2:])

    def test_remove_automaticamente_quando_excede_max_size(self) -> None:
        """Garante descarte automatico do candle mais antigo."""
        history = CandleHistory(max_size=2)
        candles = [self._candle(index) for index in range(3)]

        for candle in candles:
            history.add_candle(candle)

        self.assertEqual(history.count(), 2)
        self.assertEqual(history.last_n(2), candles[1:])

    def _candle(self, index: int) -> Candle:
        return Candle(
            data=f"2026-06-26 09:0{index}",
            abertura=100 + index,
            maxima=110 + index,
            minima=90 + index,
            fechamento=105 + index,
            volume=1000 + index,
        )


if __name__ == "__main__":
    unittest.main()
