"""Testes do contrato oficial de bolsas suportadas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.instruments.exchange import (
    B3_EXCHANGE,
    FUTURE_EXCHANGE_IDS,
    SUPPORTED_EXCHANGES,
    Exchange,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExchangeTest(unittest.TestCase):
    """Valida contrato imutavel de bolsas suportadas."""

    def test_exchange_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Exchange))
        self.assertTrue(Exchange.__dataclass_params__.frozen)

    def test_exchange_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Exchange)],
            [
                "exchange_id",
                "name",
                "timezone",
                "country",
                "currency",
                "calendar_id",
                "metadata",
            ],
        )

    def test_exchange_possui_type_hints_explicitos(self) -> None:
        annotations = Exchange.__annotations__

        self.assertEqual(annotations["exchange_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["timezone"], "str")
        self.assertEqual(annotations["country"], "str")
        self.assertEqual(annotations["currency"], "str")
        self.assertEqual(annotations["calendar_id"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_exchange_representa_bolsa(self) -> None:
        exchange = Exchange(
            exchange_id="B3",
            name="Brasil, Bolsa, Balcao",
            timezone="America/Sao_Paulo",
            country="BR",
            currency="BRL",
            calendar_id="B3",
            metadata={"status": "supported"},
        )

        self.assertEqual(exchange.exchange_id, "B3")
        self.assertEqual(exchange.name, "Brasil, Bolsa, Balcao")
        self.assertEqual(exchange.timezone, "America/Sao_Paulo")
        self.assertEqual(exchange.country, "BR")
        self.assertEqual(exchange.currency, "BRL")
        self.assertEqual(exchange.calendar_id, "B3")
        self.assertEqual(exchange.metadata["status"], "supported")

    def test_exchange_e_imutavel(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            B3_EXCHANGE.currency = "USD"

    def test_primeira_versao_registra_apenas_b3(self) -> None:
        self.assertEqual(SUPPORTED_EXCHANGES, (B3_EXCHANGE,))
        self.assertEqual(B3_EXCHANGE.exchange_id, "B3")

    def test_prepara_ids_futuros_sem_registrar_integracao(self) -> None:
        self.assertEqual(
            FUTURE_EXCHANGE_IDS,
            ("CME", "NYSE", "NASDAQ", "ICE"),
        )
        self.assertNotIn("CME", tuple(item.exchange_id for item in SUPPORTED_EXCHANGES))

    def test_exchange_nao_implementa_logica_operacional(self) -> None:
        public_methods = [
            name for name in dir(Exchange)
            if not name.startswith("_") and callable(getattr(Exchange, name))
        ]

        self.assertEqual(public_methods, [])

    def test_exchange_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("market/instruments/exchange.py")
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
            "connect",
            "download",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_exchange_nao_contem_integracao_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/instruments/exchange.py"))
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
            "requests",
            "http",
            "api",
            "socket",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
