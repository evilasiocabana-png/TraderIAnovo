"""Testes do servico de pesquisa quantitativa."""

import unittest

from application.research_service import ResearchData, ResearchService
from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import MarketRegime, RegimeAnalysis


class ResearchServiceTest(unittest.TestCase):
    """Valida exposicao do ResearchEngine pela camada de aplicacao."""

    def test_analyze_retorna_research_data(self) -> None:
        """Garante retorno do DTO de aplicacao."""
        memory = MarketMemory()
        memory.remember(self._feature_snapshot(), self._regime())

        data = ResearchService().analyze(
            self._feature_snapshot(),
            self._regime(),
            memory,
        )

        self.assertIsInstance(data, ResearchData)
        self.assertEqual(data.similar_scenarios, 1)
        self.assertEqual(data.confidence, 1.0)
        self.assertEqual(data.historical_score, 1.0)
        self.assertEqual(data.average_momentum, 10)
        self.assertEqual(data.average_trend_strength, 1.0)
        self.assertEqual(data.history_strength, "Historico fraco")
        self.assertTrue(data.summary)

    def test_analyze_sem_historico_retorna_dados_neutros(self) -> None:
        """Garante DTO neutro quando nao ha memoria similar."""
        data = ResearchService().analyze(
            self._feature_snapshot(),
            self._regime(),
            MarketMemory(),
        )

        self.assertEqual(data.similar_scenarios, 0)
        self.assertEqual(data.confidence, 0.0)
        self.assertEqual(data.average_momentum, 0.0)
        self.assertEqual(data.history_strength, "Sem historico")

    def _feature_snapshot(self) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=10,
            average_range=10,
            highest_high=120,
            lowest_low=90,
            direction="UP",
            candles_count=2,
            trend_strength=1.0,
            volatility_level="MEDIUM",
        )

    def _regime(self) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=MarketRegime.TREND,
            confidence=0.70,
            description="Mercado com predominancia direcional.",
        )


if __name__ == "__main__":
    unittest.main()
