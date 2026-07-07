"""Testes do validador de definicoes de features."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from market.features.feature_definition import FeatureDefinition
from market.features.feature_validator import (
    FeatureValidationResult,
    FeatureValidator,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class FeatureValidatorTest(unittest.TestCase):
    """Valida checagens declarativas de features registradas."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(FeatureValidationResult))
        self.assertTrue(FeatureValidationResult.__dataclass_params__.frozen)

    def test_validator_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(FeatureValidator))
        self.assertTrue(FeatureValidator.__dataclass_params__.frozen)

    def test_aprova_feature_com_campos_obrigatorios(self) -> None:
        result = FeatureValidator().validate(self._feature())

        self.assertTrue(result.is_valid)
        self.assertEqual(result.validation_messages, ())

    def test_reprova_nome_vazio(self) -> None:
        result = FeatureValidator().validate(replace(self._feature(), name=""))

        self.assertFalse(result.is_valid)
        self.assertIn("Nome da feature nao preenchido.", result.validation_messages)

    def test_reprova_categoria_vazia(self) -> None:
        result = FeatureValidator().validate(replace(self._feature(), category=""))

        self.assertFalse(result.is_valid)
        self.assertIn("Categoria da feature nao definida.", result.validation_messages)

    def test_reprova_timeframe_vazio(self) -> None:
        result = FeatureValidator().validate(replace(self._feature(), timeframe=""))

        self.assertFalse(result.is_valid)
        self.assertIn("Timeframe da feature nao definido.", result.validation_messages)

    def test_reprova_versao_nao_definida(self) -> None:
        result = FeatureValidator().validate(replace(self._feature(), version=0))

        self.assertFalse(result.is_valid)
        self.assertIn("Versao da feature nao definida.", result.validation_messages)

    def test_reprova_feature_desabilitada(self) -> None:
        result = FeatureValidator().validate(replace(self._feature(), enabled=False))

        self.assertFalse(result.is_valid)
        self.assertIn("Feature desabilitada.", result.validation_messages)

    def test_acumula_mensagens_de_campos_invalidos(self) -> None:
        feature = replace(
            self._feature(),
            name="",
            category="",
            timeframe="",
            version=0,
            enabled=False,
        )

        result = FeatureValidator().validate(feature)

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.validation_messages), 5)

    def test_resultado_e_imutavel(self) -> None:
        result = FeatureValidator().validate(self._feature())

        with self.assertRaises(FrozenInstanceError):
            result.is_valid = False

    def test_validator_nao_calcula_indicadores_ou_executa_pipeline(self) -> None:
        source = read_source(Path("market/features/feature_validator.py"))
        forbidden_fragments = (
            "FeatureEngine",
            "FeaturePipeline",
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
        path = Path("market/features/feature_validator.py")
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
            "calculate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _feature(self) -> FeatureDefinition:
        return FeatureDefinition(
            feature_id="Momentum",
            name="Momentum",
            description="Definicao declarativa de momentum.",
            category="price_action",
            timeframe="1m",
            data_type="float",
            source="market_data",
            version=1,
            author="TraderIA",
            created_at="2026-06-27T22:20:00-03:00",
            enabled=True,
        )


if __name__ == "__main__":
    unittest.main()
