"""Testes do pipeline de preparacao de dados de mercado."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from market.data.candle_validator import CandleValidationResult
from market.data.data_pipeline import DataPipeline, NormalizedMarketData
from market.data.market_data_contract import MarketDataContract
from market.data.market_data_quality_engine import MarketDataQualityResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DataPipelineTest(unittest.TestCase):
    """Valida orquestracao dos componentes de dados de mercado."""

    def test_componentes_sao_dataclasses_frozen(self) -> None:
        self.assertTrue(is_dataclass(NormalizedMarketData))
        self.assertTrue(NormalizedMarketData.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(DataPipeline))
        self.assertTrue(DataPipeline.__dataclass_params__.frozen)

    def test_prepare_retorna_normalized_market_data(self) -> None:
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            self._candle("2026-06-27T09:01:00-03:00"),
        )

        result = DataPipeline().prepare(candles)

        self.assertIsInstance(result, NormalizedMarketData)
        self.assertIs(result.candles, candles)
        self.assertEqual(len(result.validation_results), 2)
        self.assertIsInstance(result.quality_result, MarketDataQualityResult)

    def test_prepare_orquestra_validator_e_quality_engine(self) -> None:
        calls: list[str] = []
        candles = (
            self._candle("2026-06-27T09:00:00-03:00"),
            self._candle("2026-06-27T09:01:00-03:00"),
        )
        pipeline = DataPipeline(
            candle_validator=_SpyCandleValidator(calls),
            quality_engine=_SpyQualityEngine(calls),
        )

        result = pipeline.prepare(candles)

        self.assertEqual(calls, ["validate", "validate", "evaluate"])
        self.assertEqual(
            result.validation_results,
            (
                CandleValidationResult(True, ()),
                CandleValidationResult(True, ()),
            ),
        )
        self.assertEqual(result.quality_result.total_candles, 2)

    def test_prepare_preserva_candles_sem_modificar(self) -> None:
        invalid = replace(self._candle("2026-06-27T09:00:00-03:00"), volume=-1.0)
        candles = (invalid,)

        result = DataPipeline().prepare(candles)

        self.assertIs(result.candles[0], invalid)
        self.assertEqual(invalid.volume, -1.0)

    def test_normalized_market_data_e_imutavel(self) -> None:
        result = DataPipeline().prepare(())

        with self.assertRaises(FrozenInstanceError):
            result.candles = ()

    def test_pipeline_nao_realiza_validacao_ou_metricas_diretamente(self) -> None:
        source = read_source(Path("market/data/data_pipeline.py"))
        forbidden_fragments = (
            "datetime",
            "isfinite",
            "fromisoformat",
            "duplicated_candles =",
            "missing_candles =",
            "quality_score =",
            "high < low",
            "volume < 0",
            "sum(",
            "max(",
            "min(",
            "round(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_pipeline_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/data/data_pipeline.py")
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


class _SpyCandleValidator:
    """Validador de teste que registra chamadas."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def validate(self, candle: MarketDataContract) -> CandleValidationResult:
        self.calls.append("validate")
        return CandleValidationResult(True, ())


class _SpyQualityEngine:
    """Engine de teste que registra chamadas."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def evaluate(
        self,
        candles: tuple[MarketDataContract, ...],
    ) -> MarketDataQualityResult:
        self.calls.append("evaluate")
        return MarketDataQualityResult(
            total_candles=len(candles),
            valid_candles=len(candles),
            invalid_candles=0,
            missing_candles=0,
            duplicated_candles=0,
            quality_score=100.0,
        )


if __name__ == "__main__":
    unittest.main()
