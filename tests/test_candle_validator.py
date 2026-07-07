"""Testes do validador estrutural de candles."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from math import inf, nan
from pathlib import Path
import unittest

from market.data.candle_validator import CandleValidationResult, CandleValidator
from market.data.market_data_contract import MarketDataContract
from tests.architecture_test_utils import calls_from, imports_from, read_source


class CandleValidatorTest(unittest.TestCase):
    """Valida consistencia estrutural de candles normalizados."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CandleValidationResult))
        self.assertTrue(CandleValidationResult.__dataclass_params__.frozen)

    def test_validator_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CandleValidator))
        self.assertTrue(CandleValidator.__dataclass_params__.frozen)

    def test_aprova_candle_valido(self) -> None:
        result = CandleValidator().validate(self._candle())

        self.assertTrue(result.is_valid)
        self.assertEqual(result.validation_messages, ())

    def test_reprova_timestamp_invalido(self) -> None:
        result = CandleValidator().validate(
            replace(self._candle(), timestamp="not-a-date")
        )

        self.assertFalse(result.is_valid)
        self.assertIn("Timestamp do candle invalido.", result.validation_messages)

    def test_reprova_ohlc_com_high_menor_que_low(self) -> None:
        result = CandleValidator().validate(
            replace(self._candle(), high=990.0, low=1000.0)
        )

        self.assertFalse(result.is_valid)
        self.assertIn("OHLC inconsistente: high menor que low.", result.validation_messages)

    def test_reprova_open_ou_close_fora_do_intervalo(self) -> None:
        result = CandleValidator().validate(
            replace(self._candle(), open=1020.0, close=980.0)
        )

        self.assertFalse(result.is_valid)
        self.assertIn("OHLC inconsistente: open fora do intervalo.", result.validation_messages)
        self.assertIn("OHLC inconsistente: close fora do intervalo.", result.validation_messages)

    def test_reprova_volume_negativo(self) -> None:
        result = CandleValidator().validate(replace(self._candle(), volume=-1.0))

        self.assertFalse(result.is_valid)
        self.assertIn("Volume do candle negativo.", result.validation_messages)

    def test_reprova_valores_numericos_invalidos(self) -> None:
        result_nan = CandleValidator().validate(replace(self._candle(), close=nan))
        result_inf = CandleValidator().validate(replace(self._candle(), high=inf))

        self.assertFalse(result_nan.is_valid)
        self.assertFalse(result_inf.is_valid)
        self.assertIn(
            "Valores numericos do candle invalidos.",
            result_nan.validation_messages,
        )
        self.assertIn(
            "Valores numericos do candle invalidos.",
            result_inf.validation_messages,
        )

    def test_reprova_candle_incompleto(self) -> None:
        result = CandleValidator().validate(
            replace(self._candle(), symbol="", timeframe="", timestamp="")
        )

        self.assertFalse(result.is_valid)
        self.assertIn("Simbolo do candle nao definido.", result.validation_messages)
        self.assertIn("Timeframe do candle nao definido.", result.validation_messages)
        self.assertIn("Timestamp do candle nao definido.", result.validation_messages)

    def test_nao_modifica_candle_recebido(self) -> None:
        candle = replace(self._candle(), volume=-1.0)

        CandleValidator().validate(candle)

        self.assertEqual(candle.volume, -1.0)

    def test_resultado_e_imutavel(self) -> None:
        result = CandleValidator().validate(self._candle())

        with self.assertRaises(FrozenInstanceError):
            result.is_valid = False

    def test_validator_nao_calcula_indicadores_ou_executa_pipeline(self) -> None:
        source = read_source(Path("market/data/candle_validator.py"))
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
            ".calculate(",
            ".build(",
            "next_candle",
            "sum(",
            "max(",
            "min(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_validator_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/data/candle_validator.py")
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
            "calculate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _candle(self) -> MarketDataContract:
        return MarketDataContract(
            symbol="WDO",
            timeframe="1m",
            timestamp="2026-06-27T09:00:00-03:00",
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
