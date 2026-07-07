"""Testes do pipeline oficial de features."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from market.features.feature_definition import FeatureDefinition
from market.features.feature_pipeline import (
    FeatureExecutionResult,
    FeaturePipeline,
    FeatureReport,
)
from market.features.feature_registry import FeatureRegistry
from tests.architecture_test_utils import calls_from, imports_from, read_source


class FeaturePipelineTest(unittest.TestCase):
    """Valida coordenacao ordenada de features."""

    def test_componentes_sao_dataclasses_frozen(self) -> None:
        self.assertTrue(is_dataclass(FeatureExecutionResult))
        self.assertTrue(FeatureExecutionResult.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(FeatureReport))
        self.assertTrue(FeatureReport.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(FeaturePipeline))
        self.assertTrue(FeaturePipeline.__dataclass_params__.frozen)

    def test_pipeline_executa_features_na_ordem_configurada(self) -> None:
        calls: list[str] = []
        features = self._ordered_features()

        report = FeaturePipeline().execute(
            candles=("c1", "c2"),
            features=features,
            executors={
                "ATR": self._executor("ATR", 1.0, calls),
                "EMA": self._executor("EMA", 2.0, calls),
                "VWAP": self._executor("VWAP", 3.0, calls),
            },
        )

        self.assertEqual(calls, ["ATR", "EMA", "VWAP"])
        self.assertEqual(report.ordered_feature_ids, ("ATR", "EMA", "VWAP"))
        self.assertTrue(report.success)
        self.assertEqual(report.skipped_feature_ids, ())

    def test_pipeline_retorna_feature_report_tipado(self) -> None:
        report = FeaturePipeline().execute(
            candles=(),
            features=self._ordered_features(),
            executors={
                "ATR": lambda candles: 1.0,
                "EMA": lambda candles: 2.0,
                "VWAP": lambda candles: 3.0,
            },
        )

        self.assertIsInstance(report, FeatureReport)
        self.assertTrue(
            all(
                isinstance(result, FeatureExecutionResult)
                for result in report.results
            )
        )
        self.assertEqual(
            tuple(result.value for result in report.results),
            (1.0, 2.0, 3.0),
        )

    def test_pipeline_marca_feature_sem_executor_como_skipped(self) -> None:
        report = FeaturePipeline().execute(
            candles=(),
            features=self._ordered_features(),
            executors={
                "ATR": lambda candles: 1.0,
                "VWAP": lambda candles: 3.0,
            },
        )

        self.assertFalse(report.success)
        self.assertEqual(report.skipped_feature_ids, ("EMA",))
        self.assertEqual(report.results[1].feature_id, "EMA")
        self.assertFalse(report.results[1].success)
        self.assertIsNone(report.results[1].value)

    def test_pipeline_aceita_ordem_oficial_do_registry(self) -> None:
        features = FeatureRegistry().list()
        executors = {
            feature.feature_id: self._constant_executor(feature.feature_id)
            for feature in features
        }

        report = FeaturePipeline().execute(
            candles=("c1",),
            features=features,
            executors=executors,
        )

        self.assertEqual(
            report.ordered_feature_ids,
            (
                "ATR",
                "EMA",
                "VWAP",
                "OpeningRange",
                "Momentum",
                "Volume",
                "Volatility",
                "Liquidity",
                "Session",
                "Regime",
            ),
        )
        self.assertTrue(report.success)

    def test_report_e_imutavel(self) -> None:
        report = FeaturePipeline().execute(
            candles=(),
            features=self._ordered_features(),
            executors={
                "ATR": lambda candles: 1.0,
                "EMA": lambda candles: 2.0,
                "VWAP": lambda candles: 3.0,
            },
        )

        with self.assertRaises(FrozenInstanceError):
            report.success = False

    def test_pipeline_nao_contem_indicadores_embutidos(self) -> None:
        source = read_source(Path("market/features/feature_pipeline.py"))
        forbidden_fragments = (
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
            "ATR(",
            "EMA(",
            "VWAP(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_pipeline_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/features/feature_pipeline.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
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
            "validate",
            "calculate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _ordered_features(self) -> tuple[FeatureDefinition, ...]:
        registry = FeatureRegistry()
        return (
            registry.get("ATR"),
            registry.get("EMA"),
            registry.get("VWAP"),
        )

    def _executor(
        self,
        feature_id: str,
        value: float,
        calls: list[str],
    ):
        def handler(candles):
            calls.append(feature_id)
            return value

        return handler

    def _constant_executor(self, feature_id: str):
        return lambda candles: feature_id


if __name__ == "__main__":
    unittest.main()
