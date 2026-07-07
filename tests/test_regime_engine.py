"""Testes do motor independente de regime de mercado."""

import unittest

from domain.contracts.market_snapshot import MarketSnapshot
from market.regime_engine import MarketRegime, RegimeAnalysis, RegimeEngine


class RegimeEngineTest(unittest.TestCase):
    """Valida classificacoes simples de regime."""

    def test_classifica_baixa_liquidez(self) -> None:
        """Baixa liquidez deve prevalecer."""
        analysis = RegimeEngine().analyze(self._snapshot(liquidity=100))

        self.assertEqual(analysis.regime, MarketRegime.LOW_LIQUIDITY)

    def test_classifica_alta_volatilidade(self) -> None:
        """Alta volatilidade deve ser reconhecida."""
        analysis = RegimeEngine().analyze(self._snapshot(volatility=90))

        self.assertEqual(analysis.regime, MarketRegime.HIGH_VOLATILITY)

    def test_classifica_baixa_volatilidade(self) -> None:
        """Baixa volatilidade deve ser reconhecida."""
        analysis = RegimeEngine().analyze(self._snapshot(volatility=10))

        self.assertEqual(analysis.regime, MarketRegime.LOW_VOLATILITY)

    def test_classifica_trend(self) -> None:
        """Forca de tendencia alta deve virar TREND."""
        analysis = RegimeEngine().analyze(self._snapshot(trend_strength=0.9))

        self.assertEqual(analysis.regime, MarketRegime.TREND)

    def test_retorna_regime_analysis(self) -> None:
        """Resultado deve usar o contrato RegimeAnalysis."""
        analysis = RegimeEngine().analyze(self._snapshot())

        self.assertIsInstance(analysis, RegimeAnalysis)
        self.assertGreaterEqual(analysis.confidence, 0)
        self.assertTrue(analysis.description)

    def _snapshot(
        self,
        volatility: float = 30.0,
        liquidity: float = 1000.0,
        trend_strength: float = 0.4,
        regime: str = "NEUTRO",
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:00",
            regime=regime,
            volatility=volatility,
            liquidity=liquidity,
            trend_strength=trend_strength,
            market_dna_score=0.0,
        )


if __name__ == "__main__":
    unittest.main()
