"""Testes do avaliador de qualidade de dados de mercado."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from market.data.market_data_contract import MarketDataContract
from market.data.market_data_quality_engine import (
    MarketDataQualityEngine,
    MarketDataQualityResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MarketDataQualityEngineTest(unittest.TestCase):
    """Valida estatisticas de qualidade sobre candles normalizados."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketDataQualityResult))
        self.assertTrue(MarketDataQualityResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketDataQualityEngine))
        self.assertTrue(MarketDataQualityEngine.__dataclass_params__.frozen)

    def test_avalia_total_validos_invalidos_e_score_perfeito(self) -> None:
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            self._candle("2026-06-27T09:01:00-03:00"),
            self._candle("2026-06-27T09:02:00-03:00"),
        )

        result = MarketDataQualityEngine().evaluate(candles)

        self.assertEqual(result.total_candles, 3)
        self.assertEqual(result.valid_candles, 3)
        self.assertEqual(result.invalid_candles, 0)
        self.assertEqual(result.missing_candles, 0)
        self.assertEqual(result.duplicated_candles, 0)
        self.assertEqual(result.quality_score, 100.0)

    def test_conta_candles_invalidos(self) -> None:
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            replace(
                self._candle("2026-06-27T09:01:00-03:00"),
                is_valid=False,
            ),
        )

        result = MarketDataQualityEngine().evaluate(candles)

        self.assertEqual(result.total_candles, 2)
        self.assertEqual(result.valid_candles, 1)
        self.assertEqual(result.invalid_candles, 1)
        self.assertEqual(result.quality_score, 50.0)

    def test_detecta_candles_duplicados(self) -> None:
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            self._candle("2026-06-27T09:00:00-03:00"),
        )

        result = MarketDataQualityEngine().evaluate(candles)

        self.assertEqual(result.duplicated_candles, 1)
        self.assertEqual(result.quality_score, 50.0)

    def test_detecta_candles_faltantes_por_timeframe(self) -> None:
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            self._candle("2026-06-27T09:03:00-03:00"),
        )

        result = MarketDataQualityEngine().evaluate(candles)

        self.assertEqual(result.missing_candles, 2)
        self.assertEqual(result.quality_score, 50.0)

    def test_retorna_zero_para_colecao_vazia(self) -> None:
        result = MarketDataQualityEngine().evaluate(())

        self.assertEqual(result.total_candles, 0)
        self.assertEqual(result.valid_candles, 0)
        self.assertEqual(result.invalid_candles, 0)
        self.assertEqual(result.missing_candles, 0)
        self.assertEqual(result.duplicated_candles, 0)
        self.assertEqual(result.quality_score, 0.0)

    def test_nao_modifica_candles_recebidos(self) -> None:
        candle = replace(self._candle("2026-06-27T09:00:00-03:00"), is_valid=False)

        MarketDataQualityEngine().evaluate((candle,))

        self.assertFalse(candle.is_valid)

    def test_resultado_e_imutavel(self) -> None:
        result = MarketDataQualityEngine().evaluate(())

        with self.assertRaises(FrozenInstanceError):
            result.quality_score = 100.0

    def test_engine_nao_gera_features_ou_executa_replay(self) -> None:
        source = read_source(Path("market/data/market_data_quality_engine.py"))
        forbidden_fragments = (
            "FeaturePipeline",
            "FeatureEngine",
            "Alpha001",
            "ReplayEngine",
            "ResearchPipeline",
            "DecisionPipeline",
            "Broker",
            "MT5",
            "generate_signal",
            ".run(",
            ".build(",
            "next_candle",
            "order_send",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/data/market_data_quality_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
            "market.features.feature_pipeline",
            "FeaturePipeline",
            "FeatureEngine",
            "alpha",
            "strategies",
            "research.research_pipeline",
            "core.decision_pipeline",
            "DecisionPipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _candle(self, timestamp: str) -> MarketDataContract:
        return MarketDataContract(
            symbol="WDO",
            timeframe="1m",
            timestamp=timestamp,
            open=1000.0,
            high=1010.0,
            low=990.0,
            close=1005.0,
            volume=1200.0,
            is_valid=True,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
