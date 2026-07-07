"""Testes do validador de momentum da Alpha 001."""

import unittest

from alpha.momentum_validator import MomentumResult, MomentumValidator
from domain.candle import Candle


class MomentumValidatorTest(unittest.TestCase):
    """Valida confirmacao de momentum por candles recentes."""

    def test_aprova_buy_com_momentum_positivo(self) -> None:
        """BUY deve aprovar quando fechamento atual sobe."""
        result = MomentumValidator().validate(self._candles(100.0, 110.0), "BUY")

        self.assertTrue(result.approved)
        self.assertEqual(result.direction, "BUY")
        self.assertEqual(result.reason, "momentum comprador")

    def test_rejeita_buy_sem_momentum(self) -> None:
        """BUY deve rejeitar quando fechamento atual nao sobe."""
        result = MomentumValidator().validate(self._candles(110.0, 100.0), "BUY")

        self.assertFalse(result.approved)
        self.assertEqual(result.direction, "BUY")
        self.assertEqual(result.reason, "sem momentum comprador")

    def test_aprova_sell_com_momentum_negativo(self) -> None:
        """SELL deve aprovar quando fechamento atual cai."""
        result = MomentumValidator().validate(self._candles(110.0, 100.0), "SELL")

        self.assertTrue(result.approved)
        self.assertEqual(result.direction, "SELL")
        self.assertEqual(result.reason, "momentum vendedor")

    def test_rejeita_sell_sem_momentum(self) -> None:
        """SELL deve rejeitar quando fechamento atual nao cai."""
        result = MomentumValidator().validate(self._candles(100.0, 110.0), "SELL")

        self.assertFalse(result.approved)
        self.assertEqual(result.direction, "SELL")
        self.assertEqual(result.reason, "sem momentum vendedor")

    def test_rejeita_quando_houver_menos_de_dois_candles(self) -> None:
        """Sem dois candles, nao ha momentum validavel."""
        result = MomentumValidator().validate([self._candle(100.0)], "BUY")

        self.assertFalse(result.approved)
        self.assertEqual(result.direction, "WAIT")
        self.assertEqual(result.strength, 0.0)
        self.assertEqual(result.reason, "candles insuficientes")

    def test_rejeita_direction_wait(self) -> None:
        """WAIT deve rejeitar validacao de momentum."""
        result = MomentumValidator().validate(self._candles(100.0, 110.0), "WAIT")

        self.assertFalse(result.approved)
        self.assertEqual(result.direction, "WAIT")
        self.assertEqual(result.strength, 0.0)
        self.assertEqual(result.reason, "sem rompimento para validar")

    def test_valida_strength(self) -> None:
        """Strength deve refletir distancia entre fechamentos."""
        buy_result = MomentumValidator().validate(
            self._candles(100.0, 112.5),
            "BUY",
        )
        sell_result = MomentumValidator().validate(
            self._candles(112.5, 100.0),
            "SELL",
        )

        self.assertEqual(buy_result.strength, 12.5)
        self.assertEqual(sell_result.strength, 12.5)

    def test_valida_reason(self) -> None:
        """Reason deve explicar aprovacao ou rejeicao."""
        validator = MomentumValidator()

        self.assertEqual(
            validator.validate(self._candles(100.0, 110.0), "BUY").reason,
            "momentum comprador",
        )
        self.assertEqual(
            validator.validate(self._candles(110.0, 100.0), "SELL").reason,
            "momentum vendedor",
        )

    def test_valida_retorno_momentum_result(self) -> None:
        """Validator deve retornar MomentumResult."""
        result = MomentumValidator().validate(self._candles(100.0, 110.0), "BUY")

        self.assertIsInstance(result, MomentumResult)

    def _candles(self, previous_close: float, current_close: float) -> list[Candle]:
        return [self._candle(previous_close), self._candle(current_close)]

    def _candle(self, close: float) -> Candle:
        return Candle(
            data="2026-06-26 09:16",
            abertura=close,
            maxima=close + 5.0,
            minima=close - 5.0,
            fechamento=close,
            volume=1000,
        )


if __name__ == "__main__":
    unittest.main()
