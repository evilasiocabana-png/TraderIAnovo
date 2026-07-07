"""Testes da classificacao oficial das classes de ativos."""

from enum import Enum
from pathlib import Path
import unittest

from market.instruments.asset_class import AssetClass
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AssetClassTest(unittest.TestCase):
    """Valida enum puro de classes de ativos."""

    def test_asset_class_e_enum(self) -> None:
        self.assertTrue(issubclass(AssetClass, Enum))

    def test_asset_class_define_valores_oficiais(self) -> None:
        self.assertEqual(
            [item.name for item in AssetClass],
            [
                "FUTURES",
                "STOCKS",
                "ETF",
                "FOREX",
                "CRYPTO",
                "COMMODITIES",
                "FIXED_INCOME",
            ],
        )
        self.assertEqual(
            [item.value for item in AssetClass],
            [
                "FUTURES",
                "STOCKS",
                "ETF",
                "FOREX",
                "CRYPTO",
                "COMMODITIES",
                "FIXED_INCOME",
            ],
        )

    def test_asset_class_nao_executa_logica(self) -> None:
        public_methods = [
            name for name in dir(AssetClass)
            if not name.startswith("_") and callable(getattr(AssetClass, name))
        ]

        self.assertEqual(public_methods, [])

    def test_asset_class_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("market/instruments/asset_class.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "market.data",
            "replay",
            "research",
            "strategies",
            "alpha",
            "core.decision_pipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "validate",
            "calculate",
            "run",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_asset_class_nao_altera_instrument(self) -> None:
        source = read_source(Path("market/instruments/instrument.py"))

        self.assertNotIn("AssetClass", source)
        self.assertNotIn("market.instruments.asset_class", source)

    def test_asset_class_nao_contem_acoplamento_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/instruments/asset_class.py"))
        forbidden_fragments = (
            "DataPipeline",
            "ReplayEngine",
            "ResearchPipeline",
            "ResearchRunner",
            "Alpha001",
            "FeatureEngine",
            "DecisionPipeline",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
