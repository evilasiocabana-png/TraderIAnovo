"""Testes da seed demonstrativa de pesquisa quantitativa."""

import unittest

from application.research_service import ResearchService
from market.feature_engine import FeatureSnapshot
from market.regime_engine import MarketRegime, RegimeAnalysis
from research.research_seed import build_demo_market_memory


class ResearchSeedTest(unittest.TestCase):
    """Valida memoria demonstrativa para pesquisa quantitativa."""

    def test_build_demo_market_memory_retorna_registros(
        self,
    ) -> None:
        """Garante que a seed cria registros em memoria."""
        memory = build_demo_market_memory()

        self.assertGreater(memory.count(), 0)

    def test_memoria_demo_possui_cenarios_variados(self) -> None:
        """Garante cenarios de exemplo exigidos pela missao."""
        memory = build_demo_market_memory()

        self.assertTrue(memory.find_by_regime("TREND"))
        self.assertTrue(memory.find_by_regime("RANGE"))
        self.assertTrue(memory.find_by_regime("HIGH_VOLATILITY"))
        self.assertTrue(memory.find_by_regime("LOW_VOLATILITY"))
        self.assertTrue(memory.find_by_direction("UP"))
        self.assertTrue(memory.find_by_direction("DOWN"))
        self.assertTrue(memory.find_by_direction("SIDEWAYS"))

    def test_research_service_retorna_resultado_com_memoria_demo(self) -> None:
        """Garante pesquisa util usando a memoria demonstrativa."""
        data = ResearchService().analyze(
            self._feature_snapshot(),
            self._regime_analysis(),
            build_demo_market_memory(),
        )

        self.assertGreater(data.similar_scenarios, 0)
        self.assertGreater(data.confidence, 0)
        self.assertTrue(data.summary)

    def _feature_snapshot(self) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=10.0,
            average_range=10.0,
            highest_high=None,
            lowest_low=None,
            direction="UP",
            candles_count=20,
            trend_strength=0.90,
            volatility_level="MEDIUM",
        )

    def _regime_analysis(self) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=MarketRegime.TREND,
            confidence=0.70,
            description="Cenario demonstrativo de pesquisa quantitativa.",
        )


if __name__ == "__main__":
    unittest.main()
