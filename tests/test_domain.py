"""Testes das entidades de dominio."""

import unittest

from domain.candle import Candle
from domain.market_state import MarketState


class DomainTest(unittest.TestCase):
    """Garante comportamento basico do dominio."""

    def test_candle_calcula_amplitude_e_direcao(self) -> None:
        """Valida amplitude e direcao do candle."""
        candle = Candle("2026-06-25 09:00", 100, 130, 90, 120, 1000)

        self.assertEqual(candle.amplitude, 40)
        self.assertEqual(candle.direcao, "ALTA")

    def test_market_state_calcula_posicao_no_dia(self) -> None:
        """Valida posicao relativa do preco no range."""
        candle = Candle("2026-06-25 09:00", 100, 130, 90, 110, 1000)
        estado = MarketState(candle, vwap=105, atr=40, pullback_pontos=10, horario=9)

        self.assertEqual(estado.posicao_no_dia, 0.5)


if __name__ == "__main__":
    unittest.main()
