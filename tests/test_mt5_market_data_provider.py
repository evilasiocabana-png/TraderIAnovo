"""Testes do adaptador read-only de market data via MT5."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
import unittest

from core.event_bus import EventBus
from core.events import NEW_CANDLE
from domain.candle import Candle
from infrastructure.market_data.mt5_market_data_provider import MT5MarketDataProvider


class FakeMT5:
    TIMEFRAME_M1 = "M1"

    def __init__(self) -> None:
        self.initialized = False
        self.initialize_calls: list[dict[str, object]] = []
        self.login_calls: list[tuple[int, str, str]] = []
        self.selected_symbols: list[tuple[str, bool]] = []
        self.requested_rates: list[tuple[str, str, int, int]] = []
        self.symbol_info_calls: list[str] = []
        self.last_error_value = (0, "OK")

    def initialize(self, **kwargs: object) -> bool:
        self.initialized = True
        self.initialize_calls.append(kwargs)
        return True

    def login(self, login: int, password: str, server: str) -> bool:
        self.login_calls.append((login, password, server))
        return True

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        self.selected_symbols.append((symbol, enabled))
        return True

    def symbol_info(self, symbol: str) -> object | None:
        self.symbol_info_calls.append(symbol)
        if symbol in {"EURUSD", "GBPUSD"}:
            return {"name": symbol, "point": 0.00001, "spread": 12}
        return None

    def symbol_info_tick(self, symbol: str) -> object | None:
        if symbol == "EURUSD":
            return SimpleNamespace(bid=1.08123, ask=1.08135)
        return None

    def copy_rates_from_pos(
        self,
        symbol: str,
        timeframe: str,
        start: int,
        count: int,
    ) -> list[dict[str, float]]:
        self.requested_rates.append((symbol, timeframe, start, count))
        return [
            {
                "time": 1_719_792_000,
                "open": 5700.0,
                "high": 5710.0,
                "low": 5690.0,
                "close": 5705.0,
                "tick_volume": 1200,
            },
            {
                "time": 1_719_792_060,
                "open": 5705.0,
                "high": 5720.0,
                "low": 5700.0,
                "close": 5715.0,
                "tick_volume": 1400,
            },
        ]

    def account_info(self) -> object:
        return SimpleNamespace(
            login=123456,
            server="Pepperstone-Demo",
            trade_mode="demo",
            trade_allowed=False,
        )

    def terminal_info(self) -> object:
        return SimpleNamespace(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            build=4150,
            connected=True,
            community_connection=True,
        )

    def last_error(self) -> tuple[int, str]:
        return self.last_error_value


class MT5MarketDataProviderTest(unittest.TestCase):
    def test_connect_usa_credenciais_externas(self) -> None:
        fake_mt5 = FakeMT5()
        provider = MT5MarketDataProvider(
            mt5_module=fake_mt5,
            login="123456",
            password="secret",
            server="Pepperstone-Demo",
            terminal_path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
        )

        self.assertTrue(provider.connect())

        self.assertTrue(fake_mt5.initialized)
        self.assertEqual(fake_mt5.login_calls, [])
        self.assertEqual(fake_mt5.initialize_calls[0]["login"], 123456)
        self.assertEqual(fake_mt5.initialize_calls[0]["password"], "secret")
        self.assertEqual(fake_mt5.initialize_calls[0]["server"], "Pepperstone-Demo")
        self.assertEqual(
            fake_mt5.initialize_calls[0]["path"],
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
        )

    def test_select_symbol_somente_habilita_leitura_do_ativo(self) -> None:
        fake_mt5 = FakeMT5()
        provider = MT5MarketDataProvider(mt5_module=fake_mt5)

        self.assertTrue(provider.select_symbol("WDO"))

        self.assertEqual(fake_mt5.selected_symbols, [("WDO", True)])

    def test_symbol_exists_usa_symbol_info_read_only(self) -> None:
        fake_mt5 = FakeMT5()
        provider = MT5MarketDataProvider(mt5_module=fake_mt5)

        self.assertTrue(provider.symbol_exists("EURUSD"))
        self.assertFalse(provider.symbol_exists("GBPJPY"))

        self.assertEqual(fake_mt5.symbol_info_calls, ["EURUSD", "GBPJPY"])
        self.assertEqual(provider.list_symbols(), ["EURUSD"])

    def test_get_candles_converte_para_candle_e_publica_new_candle(self) -> None:
        fake_mt5 = FakeMT5()
        event_bus = EventBus()
        published: list[Candle] = []
        event_bus.subscribe(NEW_CANDLE, published.append)
        provider = MT5MarketDataProvider(mt5_module=fake_mt5, event_bus=event_bus)

        candles = provider.get_candles("WDO", fake_mt5.TIMEFRAME_M1, 2)

        self.assertEqual(fake_mt5.requested_rates, [("WDO", "M1", 0, 2)])
        self.assertEqual(len(candles), 2)
        self.assertTrue(all(isinstance(candle, Candle) for candle in candles))
        self.assertTrue(all(not isinstance(candle, dict) for candle in candles))
        self.assertEqual(candles[0].abertura, 5700.0)
        self.assertEqual(candles[0].volume, 1200)
        self.assertEqual(published, candles)

    def test_get_symbol_microstructure_importa_spread_read_only(self) -> None:
        fake_mt5 = FakeMT5()
        provider = MT5MarketDataProvider(mt5_module=fake_mt5)

        microstructure = provider.get_symbol_microstructure("EURUSD")

        self.assertEqual(microstructure["bid"], 1.08123)
        self.assertEqual(microstructure["ask"], 1.08135)
        self.assertAlmostEqual(float(microstructure["spread"]), 0.00012)
        self.assertEqual(microstructure["point"], 0.00001)
        self.assertEqual(microstructure["spread_points"], 12.0)

    def test_provider_nao_expoe_capacidade_operacional(self) -> None:
        provider_source = inspect.getsource(MT5MarketDataProvider)
        forbidden_fragments = {
            "order" + "_send",
            "send" + "_order",
            "place" + "_order",
            "execute" + "_order",
            "close" + "_position",
        }

        self.assertEqual(
            [item for item in forbidden_fragments if item in provider_source],
            [],
        )

    def test_diagnose_connection_expoe_etapas_e_last_error(self) -> None:
        fake_mt5 = FakeMT5()
        provider = MT5MarketDataProvider(mt5_module=fake_mt5)

        diagnostic = provider.diagnose_connection("EURUSD", fake_mt5.TIMEFRAME_M1)

        self.assertEqual(diagnostic["connection_status"], "ONLINE")
        self.assertEqual(diagnostic["last_error_code"], 0)
        self.assertEqual(diagnostic["last_error_message"], "OK")
        self.assertEqual(diagnostic["terminal_path"], r"C:\Program Files\MetaTrader 5\terminal64.exe")
        self.assertEqual(diagnostic["build"], "4150")
        self.assertEqual(diagnostic["server"], "Pepperstone-Demo")
        self.assertEqual(diagnostic["account"], "123456")
        self.assertTrue(diagnostic["connected"])
        self.assertFalse(diagnostic["trade_allowed"])
        self.assertTrue(diagnostic["community_connection"])
        self.assertEqual(
            [step["name"] for step in diagnostic["steps"]],
            [
                "Terminal encontrado",
                "initialize()",
                "login()",
                "account_info()",
                "terminal_info()",
                "symbol_select()",
                "copy_rates_from_pos()",
            ],
        )
        self.assertTrue(all(step["status"] == "OK" for step in diagnostic["steps"]))


if __name__ == "__main__":
    unittest.main()
