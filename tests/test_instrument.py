"""Testes do contrato oficial de instrumento financeiro."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.instruments.instrument import Instrument
from tests.architecture_test_utils import calls_from, imports_from, read_source


class InstrumentTest(unittest.TestCase):
    """Valida DTO imutavel de instrumento financeiro."""

    def test_instrument_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Instrument))
        self.assertTrue(Instrument.__dataclass_params__.frozen)

    def test_instrument_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Instrument)],
            [
                "instrument_id",
                "symbol",
                "asset_class",
                "exchange",
                "currency",
                "tick_size",
                "point_value",
                "contract_size",
                "enabled",
                "metadata",
            ],
        )

    def test_instrument_possui_type_hints_explicitos(self) -> None:
        annotations = Instrument.__annotations__

        self.assertEqual(annotations["instrument_id"], "str")
        self.assertEqual(annotations["symbol"], "str")
        self.assertEqual(annotations["asset_class"], "str")
        self.assertEqual(annotations["exchange"], "str")
        self.assertEqual(annotations["currency"], "str")
        self.assertEqual(annotations["tick_size"], "float")
        self.assertEqual(annotations["point_value"], "float")
        self.assertEqual(annotations["contract_size"], "float")
        self.assertEqual(annotations["enabled"], "bool")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_instrument_representa_instrumento_financeiro(self) -> None:
        instrument = self._instrument()

        self.assertEqual(instrument.instrument_id, "B3:WDO")
        self.assertEqual(instrument.symbol, "WDO")
        self.assertEqual(instrument.asset_class, "FUTURES")
        self.assertEqual(instrument.exchange, "B3")
        self.assertEqual(instrument.currency, "BRL")
        self.assertEqual(instrument.tick_size, 0.5)
        self.assertEqual(instrument.point_value, 10.0)
        self.assertEqual(instrument.contract_size, 1.0)
        self.assertTrue(instrument.enabled)
        self.assertEqual(instrument.metadata["session"], "regular")

    def test_instrument_e_imutavel(self) -> None:
        instrument = self._instrument()

        with self.assertRaises(FrozenInstanceError):
            instrument.enabled = False

    def test_instrument_nao_implementa_logica_operacional(self) -> None:
        public_methods = [
            name for name in dir(Instrument)
            if not name.startswith("_") and callable(getattr(Instrument, name))
        ]

        self.assertEqual(public_methods, [])

    def test_instrument_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("market/instruments/instrument.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "market.data",
            "market.features",
            "market.context",
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

    def test_instrument_nao_contem_acoplamento_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/instruments/instrument.py"))
        forbidden_fragments = (
            "DataPipeline",
            "Data Lab",
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

    def _instrument(self) -> Instrument:
        return Instrument(
            instrument_id="B3:WDO",
            symbol="WDO",
            asset_class="FUTURES",
            exchange="B3",
            currency="BRL",
            tick_size=0.5,
            point_value=10.0,
            contract_size=1.0,
            enabled=True,
            metadata={"session": "regular"},
        )


if __name__ == "__main__":
    unittest.main()
