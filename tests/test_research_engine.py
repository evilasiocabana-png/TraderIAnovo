"""Testes do motor de pesquisa quantitativa."""

import unittest

from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import MarketRegime, RegimeAnalysis
from research.research_engine import ResearchEngine, ResearchResult


class ResearchEngineTest(unittest.TestCase):
    """Valida pesquisa quantitativa isolada sobre MarketMemory."""

    def test_sem_historico_retorna_confianca_zero(self) -> None:
        """Garante resultado neutro quando nao ha memoria."""
        result = ResearchEngine().analyze(
            self._feature_snapshot(),
            self._regime(),
            MarketMemory(),
        )

        self.assertIsInstance(result, ResearchResult)
        self.assertEqual(result.similar_scenarios, 0)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.historical_score, 0.0)
        self.assertEqual(result.average_momentum, 0.0)
        self.assertEqual(result.average_trend_strength, 0.0)
        self.assertEqual(result.history_strength, "Sem historico")

    def test_calcula_quantidade_e_medias_de_cenarios_similares(self) -> None:
        """Garante calculo de quantidade, momentum e tendencia medios."""
        memory = MarketMemory()
        memory.remember(
            self._feature_snapshot(momentum=10, trend_strength=1.0),
            self._regime(),
        )
        memory.remember(
            self._feature_snapshot(momentum=12, trend_strength=0.8),
            self._regime(),
        )

        result = ResearchEngine().analyze(
            self._feature_snapshot(momentum=11, trend_strength=0.9),
            self._regime(),
            memory,
        )

        self.assertEqual(result.similar_scenarios, 2)
        self.assertEqual(result.average_momentum, 11)
        self.assertEqual(result.average_trend_strength, 0.9)

    def test_confidence_interpola_linearmente_ate_cem(self) -> None:
        """Garante confianca linear conforme quantidade historica."""
        memory = MarketMemory()
        for _ in range(50):
            memory.remember(self._feature_snapshot(), self._regime())

        result = ResearchEngine().analyze(
            self._feature_snapshot(),
            self._regime(),
            memory,
        )

        self.assertEqual(result.confidence, 50.0)
        self.assertEqual(result.historical_score, 50.0)

    def test_confidence_fica_em_cem_acima_de_cem_cenarios(self) -> None:
        """Garante teto de confianca com historico robusto."""
        memory = MarketMemory()
        for _ in range(101):
            memory.remember(self._feature_snapshot(), self._regime())

        result = ResearchEngine().analyze(
            self._feature_snapshot(),
            self._regime(),
            memory,
        )

        self.assertEqual(result.confidence, 100.0)

    def test_ignora_cenarios_nao_similares(self) -> None:
        """Garante que somente similares entram na analise."""
        memory = MarketMemory()
        memory.remember(
            self._feature_snapshot(direction="DOWN"),
            self._regime(),
        )

        result = ResearchEngine().analyze(
            self._feature_snapshot(direction="UP"),
            self._regime(),
            memory,
        )

        self.assertEqual(result.similar_scenarios, 0)

    def test_historico_fraco(self) -> None:
        """Garante classificacao de 1 a 9 cenarios."""
        result = self._analyze_with_similar_scenarios(1)

        self.assertEqual(result.history_strength, "Historico fraco")
        self.assertIn("1 cenarios parecidos", result.summary)
        self.assertIn("Historico fraco", result.summary)

    def test_historico_moderado(self) -> None:
        """Garante classificacao de 10 a 49 cenarios."""
        result = self._analyze_with_similar_scenarios(10)

        self.assertEqual(result.history_strength, "Historico moderado")
        self.assertIn("10 cenarios parecidos", result.summary)

    def test_historico_forte(self) -> None:
        """Garante classificacao de 50 ou mais cenarios."""
        result = self._analyze_with_similar_scenarios(50)

        self.assertEqual(result.history_strength, "Historico forte")
        self.assertIn("50 cenarios parecidos", result.summary)

    def test_summary_sem_historico_explica_dados_demonstrativos(self) -> None:
        """Garante explicacao clara quando nao ha memoria similar."""
        result = ResearchEngine().analyze(
            self._feature_snapshot(),
            self._regime(),
            MarketMemory(),
        )

        self.assertIn("Nenhum cenario parecido", result.summary)
        self.assertIn("demonstrativos", result.summary)

    def _analyze_with_similar_scenarios(self, quantity: int) -> ResearchResult:
        memory = MarketMemory()
        for _ in range(quantity):
            memory.remember(self._feature_snapshot(), self._regime())
        return ResearchEngine().analyze(
            self._feature_snapshot(),
            self._regime(),
            memory,
        )

    def _feature_snapshot(
        self,
        momentum: float = 10,
        direction: str = "UP",
        trend_strength: float = 1.0,
    ) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=momentum,
            average_range=10,
            highest_high=120,
            lowest_low=90,
            direction=direction,
            candles_count=2,
            trend_strength=trend_strength,
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
