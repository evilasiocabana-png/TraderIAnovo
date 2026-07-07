"""Testes do motor de features de mercado."""

import unittest

from domain.candle import Candle
from market.candle_history import CandleHistory
from market.feature_engine import FeatureEngine, FeatureSnapshot


class FeatureEngineTest(unittest.TestCase):
    """Valida o calculo isolado de features de mercado."""

    def test_build_retorna_feature_snapshot(self) -> None:
        """Garante criacao do snapshot de features."""
        history = CandleHistory()
        history.add_candle(self._candle(100, 105, 95))
        history.add_candle(self._candle(110, 120, 100))

        snapshot = FeatureEngine().build(history)

        self.assertIsInstance(snapshot, FeatureSnapshot)
        self.assertEqual(snapshot.momentum, 10)
        self.assertEqual(snapshot.average_range, 15)
        self.assertEqual(snapshot.highest_high, 120)
        self.assertEqual(snapshot.lowest_low, 95)
        self.assertEqual(snapshot.direction, "UP")
        self.assertEqual(snapshot.candles_count, 2)

    def test_trend_strength_usa_momentum_sobre_range_medio(self) -> None:
        """Garante calculo da forca de tendencia."""
        history = CandleHistory()
        history.add_candle(self._candle(100, 110, 90))
        history.add_candle(self._candle(120, 130, 110))

        snapshot = FeatureEngine().build(history)

        self.assertEqual(snapshot.trend_strength, 1.0)

    def test_trend_strength_zero_quando_range_medio_zero(self) -> None:
        """Garante protecao contra divisao por zero."""
        history = CandleHistory()
        history.add_candle(self._candle(100, 100, 100))
        history.add_candle(self._candle(100, 100, 100))

        snapshot = FeatureEngine().build(history)

        self.assertEqual(snapshot.average_range, 0)
        self.assertEqual(snapshot.trend_strength, 0.0)

    def test_volatility_level_low_medium_high(self) -> None:
        """Garante classificacao simples de volatilidade."""
        self.assertEqual(self._snapshot_for_range(5).volatility_level, "LOW")
        self.assertEqual(
            self._snapshot_for_range(15).volatility_level,
            "MEDIUM",
        )
        self.assertEqual(self._snapshot_for_range(35).volatility_level, "HIGH")

    def test_get_feature_retorna_valor_do_snapshot_atual(self) -> None:
        """Garante leitura de feature por nome."""
        engine = FeatureEngine()
        engine.build(self._history([100, 110]))

        self.assertEqual(engine.get_feature("direction"), "UP")
        self.assertEqual(engine.get_feature("momentum"), 10)

    def test_get_feature_retorna_none_sem_snapshot_ou_nome_invalido(
        self,
    ) -> None:
        """Garante fallback amigavel para feature inexistente."""
        engine = FeatureEngine()

        self.assertIsNone(engine.get_feature("momentum"))
        engine.build(self._history([100, 100]))
        self.assertIsNone(engine.get_feature("inexistente"))

    def _snapshot_for_range(self, candle_range: float) -> FeatureSnapshot:
        low = 100.0
        high = low + candle_range
        history = CandleHistory()
        history.add_candle(self._candle(100, high, low))
        return FeatureEngine().build(history)

    def _history(self, closes: list[float]) -> CandleHistory:
        history = CandleHistory()
        for close in closes:
            history.add_candle(self._candle(close, close + 5, close - 5))
        return history

    def _candle(self, close: float, high: float, low: float) -> Candle:
        return Candle(
            data="2026-06-26 09:00",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=1000,
        )


if __name__ == "__main__":
    unittest.main()
