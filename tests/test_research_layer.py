"""Testes das camadas oficiais de conhecimento do Research Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
from enum import Enum
from pathlib import Path
import unittest

from research.research_layer import (
    OFFICIAL_RESEARCH_LAYER_ORDER,
    OFFICIAL_RESEARCH_LAYERS,
    ResearchLayer,
    ResearchLayerDefinition,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchLayerTest(unittest.TestCase):
    """Congela a ordem conceitual do Research Lab."""

    def test_research_layer_e_enum(self) -> None:
        self.assertTrue(issubclass(ResearchLayer, Enum))

    def test_ordem_oficial_coloca_tempo_antes_de_validacao(self) -> None:
        self.assertEqual(
            OFFICIAL_RESEARCH_LAYER_ORDER,
            (
                ResearchLayer.MARKET_DATA,
                ResearchLayer.INDICATORS,
                ResearchLayer.CONTEXT,
                ResearchLayer.STRUCTURE,
                ResearchLayer.TIME,
                ResearchLayer.MICROSTRUCTURE,
                ResearchLayer.ALPHA,
                ResearchLayer.TRADE_PLAN,
                ResearchLayer.VALIDATION,
            ),
        )
        self.assertLess(
            OFFICIAL_RESEARCH_LAYER_ORDER.index(ResearchLayer.TIME),
            OFFICIAL_RESEARCH_LAYER_ORDER.index(ResearchLayer.VALIDATION),
        )

    def test_definicoes_possuem_indices_sequenciais(self) -> None:
        self.assertEqual(
            [definition.index for definition in OFFICIAL_RESEARCH_LAYERS],
            list(range(9)),
        )

    def test_definicao_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchLayerDefinition))
        self.assertTrue(ResearchLayerDefinition.__dataclass_params__.frozen)

        definition = OFFICIAL_RESEARCH_LAYERS[0]
        with self.assertRaises(FrozenInstanceError):
            definition.title = "Outro titulo"

    def test_cada_camada_declara_pergunta_e_responsabilidade(self) -> None:
        for definition in OFFICIAL_RESEARCH_LAYERS:
            with self.subTest(layer=definition.layer.value):
                self.assertTrue(definition.title)
                self.assertTrue(definition.question.endswith("?"))
                self.assertTrue(definition.responsibility)

    def test_camadas_permanecem_declarativas_e_desacopladas(self) -> None:
        path = Path("research/research_layer.py")
        imports = imports_from(path)
        calls = calls_from(path)
        source = read_source(path)

        forbidden_imports = {
            "application",
            "dashboard_app",
            "streamlit",
            "MetaTrader5",
            "mt5",
            "replay",
            "broker",
            "infrastructure",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "execute",
            "send",
            "open",
            "write",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertNotIn("order_send", source)
        self.assertNotIn("MetaTrader5", source)


if __name__ == "__main__":
    unittest.main()
