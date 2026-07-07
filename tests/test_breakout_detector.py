"""Testes do detector de rompimento da Alpha 001."""

import unittest

from alpha.breakout_detector import BreakoutDetector, BreakoutResult
from alpha.opening_range_engine import OpeningRange


class BreakoutDetectorTest(unittest.TestCase):
    """Valida deteccao isolada de rompimento."""

    def test_buy_acima_da_maxima(self) -> None:
        """Preco acima da maxima deve gerar BUY."""
        result = BreakoutDetector().detect(self._opening_range(), 121.0)

        self.assertEqual(result.direction, "BUY")
        self.assertTrue(result.breakout)

    def test_sell_abaixo_da_minima(self) -> None:
        """Preco abaixo da minima deve gerar SELL."""
        result = BreakoutDetector().detect(self._opening_range(), 94.0)

        self.assertEqual(result.direction, "SELL")
        self.assertTrue(result.breakout)

    def test_wait_dentro_da_faixa(self) -> None:
        """Preco dentro da faixa deve gerar WAIT."""
        result = BreakoutDetector().detect(self._opening_range(), 110.0)

        self.assertEqual(result.direction, "WAIT")
        self.assertFalse(result.breakout)
        self.assertIsNone(result.breakout_price)

    def test_wait_com_opening_range_incompleta(self) -> None:
        """Faixa incompleta deve bloquear rompimento."""
        result = BreakoutDetector().detect(self._opening_range(False), 130.0)

        self.assertEqual(result.direction, "WAIT")
        self.assertFalse(result.breakout)
        self.assertIsNone(result.breakout_price)
        self.assertEqual(result.reason, "opening range incompleta")

    def test_valida_breakout_price(self) -> None:
        """Preco de rompimento deve ser preservado no resultado."""
        buy_result = BreakoutDetector().detect(self._opening_range(), 122.5)
        sell_result = BreakoutDetector().detect(self._opening_range(), 93.5)

        self.assertEqual(buy_result.breakout_price, 122.5)
        self.assertEqual(sell_result.breakout_price, 93.5)

    def test_valida_reason(self) -> None:
        """Razao deve explicar a classificacao."""
        detector = BreakoutDetector()
        buy_result = detector.detect(self._opening_range(), 121.0)
        sell_result = detector.detect(self._opening_range(), 94.0)
        wait_result = detector.detect(self._opening_range(), 100.0)

        self.assertEqual(buy_result.reason, "rompimento da maxima")
        self.assertEqual(sell_result.reason, "rompimento da minima")
        self.assertEqual(wait_result.reason, "preco dentro da opening range")

    def test_retorna_breakout_result(self) -> None:
        """Detector deve retornar o contrato BreakoutResult."""
        result = BreakoutDetector().detect(self._opening_range(), 110.0)

        self.assertIsInstance(result, BreakoutResult)

    def _opening_range(self, is_complete: bool = True) -> OpeningRange:
        return OpeningRange(
            start_time="09:00",
            end_time="09:15",
            high=120.0,
            low=95.0,
            range_size=25.0,
            is_complete=is_complete,
        )


if __name__ == "__main__":
    unittest.main()
