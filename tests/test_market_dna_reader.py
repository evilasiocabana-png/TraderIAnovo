"""Testes do leitor de MARKET DNA para apresentacao."""

import tempfile
import unittest
from pathlib import Path

from analytics.market_dna_reader import get_latest_market_dna
from market.market_dna import MarketDNA, MarketPattern


class MarketDNAReaderTest(unittest.TestCase):
    """Valida a leitura do ultimo MARKET DNA."""

    def test_retorna_none_quando_nao_ha_dados(self) -> None:
        """Garante retorno vazio quando nao existe historico."""
        with tempfile.TemporaryDirectory() as pasta:
            dna = MarketDNA(Path(pasta))

            self.assertIsNone(get_latest_market_dna(dna))

    def test_retorna_ultimo_market_dna_quando_existe(self) -> None:
        """Garante retorno do ultimo registro salvo."""
        with tempfile.TemporaryDirectory() as pasta:
            dna = MarketDNA(Path(pasta))
            primeiro = self._pattern("2026-06-24", "09:10")
            ultimo = self._pattern("2026-06-25", "09:23")

            dna.salvar(primeiro)
            dna.salvar(ultimo)

            self.assertEqual(get_latest_market_dna(dna), ultimo)

    def _pattern(self, data: str, horario: str) -> MarketPattern:
        return MarketPattern(
            data=data,
            horario=horario,
            preco=5522.0,
            amplitude=50.0,
            volume=1500,
            vwap=5516.0,
            atr=51.0,
            pullback_pontos=13.0,
            direcao="ALTA",
            posicao_no_dia=0.84,
        )


if __name__ == "__main__":
    unittest.main()
