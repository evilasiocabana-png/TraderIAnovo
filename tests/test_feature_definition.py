"""Testes do contrato oficial de definicao de feature."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.features.feature_definition import FeatureDefinition
from tests.architecture_test_utils import calls_from, imports_from, read_source


class FeatureDefinitionTest(unittest.TestCase):
    """Valida o DTO declarativo de features de mercado."""

    def test_definition_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(FeatureDefinition))
        self.assertTrue(FeatureDefinition.__dataclass_params__.frozen)

    def test_definition_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(FeatureDefinition)]

        self.assertEqual(
            field_names,
            [
                "feature_id",
                "name",
                "description",
                "category",
                "timeframe",
                "data_type",
                "source",
                "version",
                "author",
                "created_at",
                "enabled",
            ],
        )

    def test_definition_possui_type_hints_explicitos(self) -> None:
        annotations = FeatureDefinition.__annotations__

        self.assertEqual(annotations["feature_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["description"], "str")
        self.assertEqual(annotations["category"], "str")
        self.assertEqual(annotations["timeframe"], "str")
        self.assertEqual(annotations["data_type"], "str")
        self.assertEqual(annotations["source"], "str")
        self.assertEqual(annotations["version"], "int")
        self.assertEqual(annotations["author"], "str")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["enabled"], "bool")

    def test_definition_representa_feature_sem_valor_calculado(self) -> None:
        definition = self._definition()

        self.assertEqual(definition.feature_id, "feature-momentum-001")
        self.assertEqual(definition.name, "Momentum")
        self.assertEqual(definition.category, "price_action")
        self.assertEqual(definition.timeframe, "1m")
        self.assertTrue(definition.enabled)

    def test_definition_e_imutavel(self) -> None:
        definition = self._definition()

        with self.assertRaises(FrozenInstanceError):
            definition.enabled = False

    def test_definition_nao_implementa_metodos_operacionais(self) -> None:
        public_methods = [
            name for name in dir(FeatureDefinition)
            if not name.startswith("_") and callable(getattr(FeatureDefinition, name))
        ]

        self.assertEqual(public_methods, [])

    def test_definition_permanece_desacoplada_de_camadas_operacionais(self) -> None:
        path = Path("market/features/feature_definition.py")
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

    def test_definition_nao_contem_logica_operacional_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/features/feature_definition.py"))
        forbidden_fragments = (
            "ReplayEngine",
            "FeatureEngine",
            "Alpha001",
            "DecisionPipeline",
            "ResearchPipeline",
            "Broker",
            "MT5",
            "candle",
            "profit",
            "drawdown",
            "win_rate",
            "sum(",
            "max(",
            "min(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _definition(self) -> FeatureDefinition:
        return FeatureDefinition(
            feature_id="feature-momentum-001",
            name="Momentum",
            description="Definicao declarativa de momentum.",
            category="price_action",
            timeframe="1m",
            data_type="float",
            source="normalized_market_data",
            version=1,
            author="TraderIA Research",
            created_at="2026-06-27T22:00:00-03:00",
            enabled=True,
        )


if __name__ == "__main__":
    unittest.main()
