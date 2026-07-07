"""Testes da memoria estatistica de mercado."""

import unittest
from datetime import datetime

from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory, MarketMemoryRecord
from market.regime_engine import MarketRegime, RegimeAnalysis


class MarketMemoryTest(unittest.TestCase):
    """Valida armazenamento isolado de registros de memoria."""

    def test_remember_cria_registro_de_memoria(self) -> None:
        """Garante criacao de registro combinando features e regime."""
        memory = MarketMemory()

        record = memory.remember(self._feature_snapshot(), self._regime())

        self.assertIsInstance(record, MarketMemoryRecord)
        self.assertIsInstance(record.timestamp, datetime)
        self.assertEqual(record.regime, "TREND")
        self.assertEqual(record.direction, "UP")
        self.assertEqual(record.momentum, 10)
        self.assertEqual(record.volatility, "MEDIUM")
        self.assertEqual(record.trend_strength, 1.0)

    def test_count_retorna_quantidade_de_registros(self) -> None:
        """Garante contagem de registros armazenados."""
        memory = MarketMemory()

        memory.remember(self._feature_snapshot(), self._regime())
        memory.remember(self._feature_snapshot(momentum=20), self._regime())

        self.assertEqual(memory.count(), 2)

    def test_last_retorna_ultimo_registro(self) -> None:
        """Garante leitura do ultimo registro."""
        memory = MarketMemory()
        first = memory.remember(self._feature_snapshot(), self._regime())
        second = memory.remember(
            self._feature_snapshot(momentum=20),
            self._regime(),
        )

        self.assertNotEqual(memory.last(), first)
        self.assertEqual(memory.last(), second)

    def test_last_sem_registros_retorna_none(self) -> None:
        """Garante fallback quando memoria esta vazia."""
        self.assertIsNone(MarketMemory().last())

    def test_all_retorna_copia_dos_registros(self) -> None:
        """Garante que lista externa nao altera a memoria."""
        memory = MarketMemory()
        record = memory.remember(self._feature_snapshot(), self._regime())

        records = memory.all()
        records.clear()

        self.assertEqual(memory.count(), 1)
        self.assertEqual(memory.last(), record)

    def test_clear_remove_todos_os_registros(self) -> None:
        """Garante limpeza completa da memoria."""
        memory = MarketMemory()
        memory.remember(self._feature_snapshot(), self._regime())

        memory.clear()

        self.assertEqual(memory.count(), 0)
        self.assertIsNone(memory.last())

    def test_find_by_regime_retorna_registros_do_regime(self) -> None:
        """Garante busca por regime."""
        memory = MarketMemory()
        trend_record = memory.remember(
            self._feature_snapshot(),
            self._regime(),
        )
        memory.remember(
            self._feature_snapshot(),
            self._regime(MarketRegime.RANGE),
        )

        results = memory.find_by_regime("TREND")

        self.assertEqual(results, [trend_record])

    def test_find_by_direction_retorna_registros_da_direcao(self) -> None:
        """Garante busca por direcao."""
        memory = MarketMemory()
        up_record = memory.remember(self._feature_snapshot(), self._regime())
        memory.remember(
            self._feature_snapshot(direction="DOWN"),
            self._regime(),
        )

        results = memory.find_by_direction("UP")

        self.assertEqual(results, [up_record])

    def test_find_similar_retorna_cenarios_parecidos(self) -> None:
        """Garante busca por similaridade."""
        memory = MarketMemory()
        similar = memory.remember(
            self._feature_snapshot(momentum=11, trend_strength=0.90),
            self._regime(),
        )
        memory.remember(
            self._feature_snapshot(momentum=15, trend_strength=1.50),
            self._regime(),
        )

        results = memory.find_similar(
            self._feature_snapshot(momentum=10, trend_strength=1.0),
            self._regime(),
        )

        self.assertEqual(results, [similar])

    def test_find_similar_retorna_lista_vazia_sem_similar(self) -> None:
        """Garante lista vazia quando nao ha cenario similar."""
        memory = MarketMemory()
        memory.remember(
            self._feature_snapshot(momentum=30, trend_strength=2.0),
            self._regime(),
        )

        results = memory.find_similar(
            self._feature_snapshot(momentum=10, trend_strength=1.0),
            self._regime(),
        )

        self.assertEqual(results, [])

    def test_find_similar_com_zero_exige_valor_zero(self) -> None:
        """Garante comparacao segura quando valor alvo e zero."""
        memory = MarketMemory()
        zero_record = memory.remember(
            self._feature_snapshot(momentum=0, trend_strength=0),
            self._regime(),
        )
        memory.remember(
            self._feature_snapshot(momentum=1, trend_strength=0),
            self._regime(),
        )

        results = memory.find_similar(
            self._feature_snapshot(momentum=0, trend_strength=0),
            self._regime(),
        )

        self.assertEqual(results, [zero_record])

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

    def _regime(
        self,
        regime: MarketRegime = MarketRegime.TREND,
    ) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=regime,
            confidence=0.70,
            description="Mercado com predominancia direcional.",
        )


if __name__ == "__main__":
    unittest.main()
