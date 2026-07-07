"""Testes do servico de aplicacao de regime."""

import unittest

from application.regime_service import RegimeData, RegimeService
from domain.contracts.market_snapshot import MarketSnapshot


class RegimeServiceTest(unittest.TestCase):
    """Valida exposicao do RegimeEngine pela aplicacao."""

    def test_retorna_regime_data(self) -> None:
        """Garante retorno pronto para consumo da aplicacao."""
        data = RegimeService().analyze(self._snapshot())

        self.assertIsInstance(data, RegimeData)
        self.assertEqual(data.regime, "TREND")
        self.assertGreater(data.confidence, 0)
        self.assertTrue(data.description)

    def _snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:00",
            regime="ALTA",
            volatility=30.0,
            liquidity=1000.0,
            trend_strength=0.9,
            market_dna_score=0.0,
        )


if __name__ == "__main__":
    unittest.main()
