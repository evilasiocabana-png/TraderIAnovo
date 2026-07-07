"""Testes do registro oficial de features."""

from dataclasses import is_dataclass
from pathlib import Path
import unittest

from market.features.feature_definition import FeatureDefinition
from market.features.feature_registry import (
    DEFAULT_FEATURE_DEFINITIONS,
    FeatureRegistry,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class FeatureRegistryTest(unittest.TestCase):
    """Valida registro em memoria de definicoes de features."""

    def test_registry_e_dataclass(self) -> None:
        self.assertTrue(is_dataclass(FeatureRegistry))

    def test_registry_carrega_features_oficiais(self) -> None:
        registry = FeatureRegistry()

        self.assertEqual(
            tuple(feature.feature_id for feature in registry.list()),
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

    def test_definicoes_padrao_sao_feature_definition(self) -> None:
        self.assertTrue(DEFAULT_FEATURE_DEFINITIONS)
        self.assertTrue(
            all(
                isinstance(feature, FeatureDefinition)
                for feature in DEFAULT_FEATURE_DEFINITIONS
            )
        )

    def test_get_e_exists_retorna_feature_registrada(self) -> None:
        registry = FeatureRegistry()

        feature = registry.get("Momentum")

        self.assertIsInstance(feature, FeatureDefinition)
        self.assertEqual(feature.name, "Momentum")
        self.assertTrue(registry.exists("Momentum"))
        self.assertFalse(registry.exists("Unknown"))

    def test_register_substitui_feature_por_id(self) -> None:
        registry = FeatureRegistry()
        replacement = FeatureDefinition(
            feature_id="Momentum",
            name="Momentum Custom",
            description="Definicao customizada de teste.",
            category="price_action",
            timeframe="5m",
            data_type="float",
            source="test",
            version=2,
            author="Test",
            created_at="2026-06-27T22:15:00-03:00",
            enabled=True,
        )

        saved = registry.register(replacement)

        self.assertIs(saved, replacement)
        self.assertIs(registry.get("Momentum"), replacement)

    def test_unregister_remove_feature_existente(self) -> None:
        registry = FeatureRegistry()

        removed = registry.unregister("ATR")

        self.assertTrue(removed)
        self.assertIsNone(registry.get("ATR"))
        self.assertFalse(registry.exists("ATR"))

    def test_unregister_retorna_false_para_feature_inexistente(self) -> None:
        self.assertFalse(FeatureRegistry().unregister("Unknown"))

    def test_list_retorna_tuple_para_proteger_ordem_de_saida(self) -> None:
        features = FeatureRegistry().list()

        self.assertIsInstance(features, tuple)
        self.assertEqual(len(features), len(DEFAULT_FEATURE_DEFINITIONS))

    def test_registry_nao_calcula_features_ou_acessa_dados_operacionais(self) -> None:
        source = read_source(Path("market/features/feature_registry.py"))
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
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_registry_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/features/feature_registry.py")
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


if __name__ == "__main__":
    unittest.main()
