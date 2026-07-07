"""Testes do registro oficial de instrumentos financeiros."""

from pathlib import Path
import unittest

from market.instruments.instrument import Instrument
from market.instruments.instrument_registry import (
    DEFAULT_WDO_INSTRUMENT,
    FUTURE_INSTRUMENT_SYMBOLS,
    InstrumentRegistry,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class InstrumentRegistryTest(unittest.TestCase):
    """Valida registry em memoria de instrumentos suportados."""

    def test_registry_registra_wdo_por_padrao(self) -> None:
        registry = InstrumentRegistry()

        self.assertEqual(registry.list(), (DEFAULT_WDO_INSTRUMENT,))
        self.assertTrue(registry.exists("B3:WDO"))
        self.assertIs(registry.get("B3:WDO"), DEFAULT_WDO_INSTRUMENT)

    def test_default_wdo_tem_campos_esperados(self) -> None:
        self.assertEqual(DEFAULT_WDO_INSTRUMENT.instrument_id, "B3:WDO")
        self.assertEqual(DEFAULT_WDO_INSTRUMENT.symbol, "WDO")
        self.assertEqual(DEFAULT_WDO_INSTRUMENT.asset_class, "FUTURES")
        self.assertEqual(DEFAULT_WDO_INSTRUMENT.exchange, "B3")
        self.assertEqual(DEFAULT_WDO_INSTRUMENT.currency, "BRL")
        self.assertTrue(DEFAULT_WDO_INSTRUMENT.enabled)

    def test_register_substitui_instrumento(self) -> None:
        registry = InstrumentRegistry()
        updated = self._instrument("B3:WDO", symbol="WDO", enabled=False)

        saved = registry.register(updated)

        self.assertIs(saved, updated)
        self.assertIs(registry.get("B3:WDO"), updated)
        self.assertEqual(registry.list(), (updated,))

    def test_register_adiciona_novo_instrumento(self) -> None:
        registry = InstrumentRegistry()
        win = self._instrument("B3:WIN", symbol="WIN")

        registry.register(win)

        self.assertTrue(registry.exists("B3:WIN"))
        self.assertEqual(registry.get("B3:WIN"), win)
        self.assertEqual(len(registry.list()), 2)

    def test_unregister_remove_quando_existe(self) -> None:
        registry = InstrumentRegistry()

        self.assertTrue(registry.unregister("B3:WDO"))
        self.assertFalse(registry.exists("B3:WDO"))
        self.assertIsNone(registry.get("B3:WDO"))
        self.assertFalse(registry.unregister("B3:WDO"))

    def test_repositorios_sao_isolados_em_memoria(self) -> None:
        first = InstrumentRegistry()
        second = InstrumentRegistry()
        first.register(self._instrument("B3:WIN", symbol="WIN"))

        self.assertTrue(first.exists("B3:WIN"))
        self.assertFalse(second.exists("B3:WIN"))

    def test_simbolos_futuros_sao_apenas_declarativos(self) -> None:
        self.assertEqual(
            FUTURE_INSTRUMENT_SYMBOLS,
            (
                "WIN",
                "PETR4",
                "VALE3",
                "ITUB4",
                "SPY",
                "QQQ",
                "ES",
                "NQ",
                "CL",
                "GC",
                "BTC",
            ),
        )
        registered_symbols = tuple(item.symbol for item in InstrumentRegistry().list())

        self.assertEqual(registered_symbols, ("WDO",))
        self.assertNotIn("WIN", registered_symbols)
        self.assertNotIn("BTC", registered_symbols)

    def test_registry_nao_acessa_data_research_feature_ou_operacao(self) -> None:
        source = read_source(Path("market/instruments/instrument_registry.py"))
        forbidden_fragments = (
            "DataPipeline",
            "Data Lab",
            "FeatureEngine",
            "FeaturePipeline",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Alpha001",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            "open(",
            "write(",
            "read_text",
            "write_text",
            "sqlite",
            "postgres",
            "redis",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_registry_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("market/instruments/instrument_registry.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "market.data",
            "market.features",
            "market.feature_engine",
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
            "connect",
            "download",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _instrument(
        self,
        instrument_id: str,
        symbol: str,
        enabled: bool = True,
    ) -> Instrument:
        return Instrument(
            instrument_id=instrument_id,
            symbol=symbol,
            asset_class="FUTURES",
            exchange="B3",
            currency="BRL",
            tick_size=1.0,
            point_value=1.0,
            contract_size=1.0,
            enabled=enabled,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
