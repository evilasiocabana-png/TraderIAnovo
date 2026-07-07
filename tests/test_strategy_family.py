"""Testes da classificacao oficial das familias de estrategia."""

from enum import Enum
from pathlib import Path
import unittest

from strategies.strategy_family import StrategyFamily
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StrategyFamilyTest(unittest.TestCase):
    """Valida enum puro de familias de estrategia."""

    def test_strategy_family_e_enum(self) -> None:
        self.assertTrue(issubclass(StrategyFamily, Enum))

    def test_strategy_family_define_valores_oficiais(self) -> None:
        self.assertEqual(
            [item.name for item in StrategyFamily],
            [
                "INTRADAY",
                "SWING",
                "POSITION",
                "LONG_SHORT",
                "PORTFOLIO",
            ],
        )
        self.assertEqual(
            [item.value for item in StrategyFamily],
            [
                "INTRADAY",
                "SWING",
                "POSITION",
                "LONG_SHORT",
                "PORTFOLIO",
            ],
        )

    def test_strategy_family_nao_executa_logica(self) -> None:
        public_methods = [
            name for name in dir(StrategyFamily)
            if not name.startswith("_") and callable(getattr(StrategyFamily, name))
        ]

        self.assertEqual(public_methods, [])

    def test_strategy_family_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("strategies/strategy_family.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research",
            "dashboard_app",
            "streamlit",
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

    def test_strategy_family_nao_altera_alphas_existentes(self) -> None:
        checked_paths = (
            Path("strategies/alpha001_iorb_strategy.py"),
            Path("strategies/alpha002/alpha002_strategy.py"),
            Path("strategies/alpha003/alpha003_strategy.py"),
        )

        for path in checked_paths:
            with self.subTest(path=str(path)):
                source = read_source(path)
                self.assertNotIn("StrategyFamily", source)
                self.assertNotIn("strategies.strategy_family", source)

    def test_strategy_family_nao_contem_acoplamento_no_codigo_fonte(self) -> None:
        source = read_source(Path("strategies/strategy_family.py"))
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Alpha001",
            "Alpha002",
            "Alpha003",
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
