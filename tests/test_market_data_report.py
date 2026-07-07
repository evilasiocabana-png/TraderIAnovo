"""Testes do relatorio oficial do Data Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.data.candle_validator import CandleValidationResult
from market.data.market_data_contract import MarketDataContract
from market.data.market_data_quality_engine import MarketDataQualityResult
from market.data.market_data_report import MarketDataReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MarketDataReportTest(unittest.TestCase):
    """Valida consolidacao pura dos resultados do Data Lab."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketDataReport))
        self.assertTrue(MarketDataReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(MarketDataReport)]

        self.assertEqual(
            field_names,
            [
                "candles",
                "validation_results",
                "quality_result",
                "total_candles",
                "valid_candles",
                "invalid_candles",
                "duplicated_candles",
                "missing_candles",
                "quality_score",
                "execution_time",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = MarketDataReport.__annotations__

        self.assertEqual(annotations["candles"], "tuple[MarketDataContract, ...]")
        self.assertEqual(
            annotations["validation_results"],
            "tuple[CandleValidationResult, ...]",
        )
        self.assertEqual(annotations["quality_result"], "MarketDataQualityResult")
        self.assertEqual(annotations["total_candles"], "int")
        self.assertEqual(annotations["valid_candles"], "int")
        self.assertEqual(annotations["invalid_candles"], "int")
        self.assertEqual(annotations["duplicated_candles"], "int")
        self.assertEqual(annotations["missing_candles"], "int")
        self.assertEqual(annotations["quality_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.candles[0], MarketDataContract)
        self.assertIsInstance(report.validation_results[0], CandleValidationResult)
        self.assertIsInstance(report.quality_result, MarketDataQualityResult)
        self.assertEqual(report.total_candles, 1)
        self.assertEqual(report.valid_candles, 1)
        self.assertEqual(report.invalid_candles, 0)
        self.assertEqual(report.duplicated_candles, 0)
        self.assertEqual(report.missing_candles, 0)
        self.assertEqual(report.quality_score, 100.0)
        self.assertEqual(report.execution_time, 4.5)

    def test_report_preserva_referencias_recebidas(self) -> None:
        candles = (self._candle(),)
        validations = (CandleValidationResult(True, ()),)
        quality = self._quality()

        report = MarketDataReport(
            candles=candles,
            validation_results=validations,
            quality_result=quality,
            total_candles=1,
            valid_candles=1,
            invalid_candles=0,
            duplicated_candles=0,
            missing_candles=0,
            quality_score=100.0,
            execution_time=4.5,
        )

        self.assertIs(report.candles, candles)
        self.assertIs(report.validation_results, validations)
        self.assertIs(report.quality_result, quality)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.execution_time = 0.0

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(Path("market/data/market_data_report.py"))
        forbidden_fragments = (
            ".run(",
            ".execute(",
            ".prepare(",
            ".evaluate(",
            ".validate(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "len(",
            "DataPipeline",
            "CandleValidator",
            "MarketDataQualityEngine",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(Path("market/data/market_data_report.py"))
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/data/market_data_report.py")
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
            "prepare",
            "evaluate",
            "validate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> MarketDataReport:
        return MarketDataReport(
            candles=(self._candle(),),
            validation_results=(CandleValidationResult(True, ()),),
            quality_result=self._quality(),
            total_candles=1,
            valid_candles=1,
            invalid_candles=0,
            duplicated_candles=0,
            missing_candles=0,
            quality_score=100.0,
            execution_time=4.5,
        )

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

    def _quality(self) -> MarketDataQualityResult:
        return MarketDataQualityResult(
            total_candles=1,
            valid_candles=1,
            invalid_candles=0,
            missing_candles=0,
            duplicated_candles=0,
            quality_score=100.0,
        )


if __name__ == "__main__":
    unittest.main()
