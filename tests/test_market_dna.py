"""Testes do MARKET DNA."""

import tempfile
import unittest
from pathlib import Path

from domain.candle import Candle
from domain.market_state import MarketState
from market.market_dna import MarketDNA


class MarketDNATest(unittest.TestCase):
    """Valida persistencia e comparacao de padroes."""

    def test_salva_e_carrega_pattern(self) -> None:
        """Garante que um pattern persiste em JSONL."""
        with tempfile.TemporaryDirectory() as pasta:
            dna = MarketDNA(Path(pasta))
            estado = self._estado()
            pattern = dna.criar_pattern(estado)

            dna.salvar(pattern)

            self.assertEqual(len(dna.carregar()), 1)

    def _estado(self) -> MarketState:
        candle = Candle("2026-06-25 09:23", 5500, 5530, 5480, 5522, 1500)
        return MarketState(candle, vwap=5516, atr=51, pullback_pontos=13, horario=9)


if __name__ == "__main__":
    unittest.main()
