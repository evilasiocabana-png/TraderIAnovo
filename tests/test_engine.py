"""Testes do motor de trading."""

import unittest

from app import criar_engine
from core.configuration_manager import ConfigurationManager
from domain.candle import Candle
from domain.market_state import MarketState


class EngineTest(unittest.TestCase):
    """Valida a orquestracao principal."""

    def test_engine_cria_operacao_com_sinal_aprovado(self) -> None:
        """Garante que um bom contexto vira operacao."""
        configuration = ConfigurationManager.get_configuration()
        engine = criar_engine(configuration)
        candle = Candle("2026-06-25 09:23", 5500, 5530, 5480, 5522, 1500)
        estado = MarketState(candle, vwap=5516, atr=51, pullback_pontos=13, horario=9)

        operacao = engine.processar(estado)

        self.assertIsNotNone(operacao)
        self.assertEqual(operacao.tipo, "COMPRA")


if __name__ == "__main__":
    unittest.main()
