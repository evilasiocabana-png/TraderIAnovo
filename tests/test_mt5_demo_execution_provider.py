"""Testes do provider MT5 Demo sem conta real."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from domain.contracts.execution_order import ExecutionOrder
from infrastructure.execution.mt5_demo_execution_provider import (
    MT5DemoExecutionProvider,
)


class MT5DemoExecutionProviderTest(unittest.TestCase):
    """Valida isolamento e conversao para request MT5."""

    def test_bloqueia_conta_nao_demo(self) -> None:
        mt5 = _FakeMT5(trade_mode=99)
        provider = self._provider(mt5)

        result = provider.submit_order(self._order())

        self.assertFalse(result.accepted)
        self.assertIn("nao e demo", result.message)
        self.assertIsNone(mt5.last_request)

    def test_envia_order_send_quando_conta_demo(self) -> None:
        mt5 = _FakeMT5()
        provider = self._provider(mt5)

        result = provider.submit_order(self._order())

        self.assertTrue(result.accepted)
        self.assertEqual(result.ticket, 777)
        self.assertEqual(mt5.last_request["symbol"], "WDO")
        self.assertEqual(mt5.last_request["volume"], 0.1)
        self.assertEqual(mt5.last_request["sl"], 90.0)
        self.assertEqual(mt5.last_request["tp"], 120.0)
        self.assertEqual(mt5.last_request["comment"], "TraderIA M1")

    def test_rejeita_preflight_quando_preco_atual_invalida_sl_tp(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.33567, bid=1.33565)
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="GBPUSD",
                side="SELL",
                quantity=0.1,
                entry_price=1.33833,
                stop=1.33966833,
                target=1.33565334,
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("stale", result.message)
        self.assertIsNone(mt5.last_request)

    def test_bloqueia_mesmo_plano_no_mesmo_candle_do_lab(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.33712, bid=1.33710)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            order = ExecutionOrder(
                symbol="GBPUSD",
                side="SELL",
                quantity=0.1,
                entry_price=1.33833,
                stop=1.33966833,
                target=1.33565334,
                plan_identity="GBPUSD|M1|2026-07-08 21:18|ADX|TP v5",
            )

            first = provider.submit_order(order)
            second = provider.submit_order(order)

            self.assertTrue(first.accepted)
            self.assertFalse(second.accepted)
            self.assertIn("duplicado", second.message)

    def test_tentativa_rejeitada_nao_bloqueia_reenvio_do_plano(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.33712, bid=1.33710)
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "orders.jsonl"
            log_path.write_text(
                (
                    '{"symbol":"GBPUSD","side":"SELL","entry_price":1.33833,'
                    '"stop":1.33966833,"target":1.33565334,'
                    '"accepted":false,"status":"REJECTED",'
                    '"message":"Plano MT5 Demo stale",'
                    '"plan_identity":"GBPUSD|M1|2026-07-08 21:18|ADX|TP v5"}\n'
                ),
                encoding="utf-8",
            )
            provider = MT5DemoExecutionProvider(mt5=mt5, log_path=log_path)
            order = ExecutionOrder(
                symbol="GBPUSD",
                side="SELL",
                quantity=0.1,
                entry_price=1.33833,
                stop=1.33966833,
                target=1.33565334,
                plan_identity="GBPUSD|M1|2026-07-08 21:18|ADX|TP v5",
            )

            result = provider.submit_order(order)

            self.assertTrue(result.accepted)
            self.assertEqual(mt5.last_request["comment"], "TraderIA M1")

    def test_libera_mesmo_plano_quando_candle_do_lab_muda(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.33712, bid=1.33710)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            first_order = ExecutionOrder(
                symbol="GBPUSD",
                side="SELL",
                quantity=0.1,
                entry_price=1.33833,
                stop=1.33966833,
                target=1.33565334,
                plan_identity="GBPUSD|M1|2026-07-08 21:18|ADX|TP v5",
            )
            second_order = ExecutionOrder(
                symbol="GBPUSD",
                side="SELL",
                quantity=0.1,
                entry_price=1.33833,
                stop=1.33966833,
                target=1.33565334,
                plan_identity="GBPUSD|M1|2026-07-08 21:19|ADX|TP v5",
            )

            first = provider.submit_order(first_order)
            second = provider.submit_order(second_order)

            self.assertTrue(first.accepted)
            self.assertTrue(second.accepted)

    def test_has_open_position_consulta_simbolo(self) -> None:
        mt5 = _FakeMT5(open_positions=[object()])
        provider = self._provider(mt5)

        self.assertTrue(provider.has_open_position("WDO"))
        self.assertEqual(mt5.positions_symbol, "WDO")

    def test_has_open_position_for_model_diferencia_modelo_operacional(self) -> None:
        position = SimpleNamespace(comment="TraderIA M1")
        mt5 = _FakeMT5(open_positions=[position])
        provider = self._provider(mt5)

        self.assertTrue(
            provider.has_open_position_for_model("EURUSD", "MODELO_1_ALPHA_ATUAL")
        )
        self.assertFalse(
            provider.has_open_position_for_model(
                "EURUSD",
                "MODELO_2_ESPELHO_BETA2_RR1",
            )
        )

    def test_get_recent_candles_aceita_array_like_do_mt5(self) -> None:
        """copy_rates_from_pos pode retornar array com bool ambiguo."""
        candles = _AmbiguousRates(
            [
                {"time": 1, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0},
                {"time": 2, "open": 1.0, "high": 1.2, "low": 0.95, "close": 1.1},
            ]
        )
        mt5 = _FakeMT5()
        mt5.rates = candles
        provider = self._provider(mt5)

        result = provider.get_recent_candles("EURUSD", "M1", 2)

        self.assertEqual(list(result), list(candles))

    def test_registra_log_jsonl(self) -> None:
        mt5 = _FakeMT5()
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "orders.jsonl"
            provider = MT5DemoExecutionProvider(mt5=mt5, log_path=log_path)

            provider.submit_order(self._order())

            content = log_path.read_text(encoding="utf-8")
            self.assertIn('"symbol": "WDO"', content)
            self.assertIn('"accepted": true', content)

    def test_break_even_move_stop_via_sltp_quando_preco_anda_um_risco(self) -> None:
        position = SimpleNamespace(
            ticket=123,
            symbol="GBPUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.33637,
            sl=1.33508,
            tp=1.34043,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=1.33910, bid=1.33908)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
                management_log_path=Path(temp_dir) / "management.jsonl",
            )

            results = provider.apply_stop_management_from_signals(
                [
                    {
                        "symbol": "GBPUSD",
                        "decision": "BUY",
                        "entry": 1.33637,
                        "stop": 1.33508,
                        "target": 1.34043,
                        "stop_management": "BREAK_EVEN",
                        "stop_management_parameters": {
                            "break_even_trigger_rr": "1.0",
                            "break_even_offset_pips": "0.0",
                        },
                    }
                ]
            )

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["accepted"])
            self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_SLTP)
            self.assertEqual(mt5.last_request["position"], 123)
            self.assertAlmostEqual(mt5.last_request["sl"], 1.33637)
            self.assertAlmostEqual(mt5.last_request["tp"], 1.34043)

    def test_atr_trailing_move_stop_sell_quando_stop_melhora(self) -> None:
        position = SimpleNamespace(
            ticket=456,
            symbol="USDCHF",
            type=_FakeMT5.POSITION_TYPE_SELL,
            price_open=0.80656,
            sl=0.80737,
            tp=0.80414,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=0.80580, bid=0.80578)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
                management_log_path=Path(temp_dir) / "management.jsonl",
            )

            results = provider.apply_stop_management_from_signals(
                [
                    {
                        "symbol": "USDCHF",
                        "decision": "SELL",
                        "entry": 0.80656,
                        "target": 0.80414,
                        "stop_management": "ATR_TRAILING_STOP",
                        "stop_management_parameters": {
                            "atr_trailing_factor": "2.0",
                        },
                        "market_indicators": {
                            "atr": 0.00020,
                        },
                    }
                ]
            )

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["accepted"])
            self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_SLTP)
            self.assertEqual(mt5.last_request["position"], 456)
            self.assertAlmostEqual(mt5.last_request["sl"], 0.80620)
            self.assertAlmostEqual(mt5.last_request["tp"], 0.80414)

    def test_fixed_stop_nao_envia_sltp_de_gestao_movel(self) -> None:
        position = SimpleNamespace(
            ticket=789,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1040,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=1.1030, bid=1.1028)
        provider = self._provider(mt5)

        results = provider.apply_stop_management_from_signals(
            [
                {
                    "symbol": "EURUSD",
                    "decision": "BUY",
                    "entry": 1.1000,
                    "stop": 1.0980,
                    "target": 1.1040,
                    "stop_management": "FIXED_STOP",
                }
            ]
        )

        self.assertEqual(results, [])
        self.assertIsNone(mt5.last_request)

    def test_assisted_sl_demo_preserva_tp_e_usa_sltp(self) -> None:
        position = SimpleNamespace(
            ticket=321,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=1.1042, bid=1.1040)
        provider = self._provider(mt5)

        result = provider.modify_demo_position_stop_loss(
            symbol="EURUSD",
            ticket=321,
            side="BUY",
            requested_stop=1.1010,
            decision_key="candle-1",
        )

        self.assertTrue(result.success)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_SLTP)
        self.assertEqual(mt5.last_request["position"], 321)
        self.assertAlmostEqual(mt5.last_request["sl"], 1.1010)
        self.assertAlmostEqual(mt5.last_request["tp"], 1.1060)
        self.assertNotIn("volume", mt5.last_request)

    def test_assisted_sl_conta_nao_demo_rejeita_sem_order_send(self) -> None:
        position = SimpleNamespace(
            ticket=321,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
        )
        mt5 = _FakeMT5(trade_mode=99, open_positions=[position])
        provider = self._provider(mt5)

        result = provider.modify_demo_position_stop_loss(
            symbol="EURUSD",
            ticket=321,
            side="BUY",
            requested_stop=1.1010,
        )

        self.assertFalse(result.success)
        self.assertIn("nao e demo", result.message)
        self.assertIsNone(mt5.last_request)

    def test_assisted_sl_rejeita_stop_que_nao_melhora(self) -> None:
        position = SimpleNamespace(
            ticket=654,
            symbol="USDCHF",
            type=_FakeMT5.POSITION_TYPE_SELL,
            price_open=0.8060,
            sl=0.8070,
            tp=0.8030,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=0.8050, bid=0.8048)
        provider = self._provider(mt5)

        result = provider.modify_demo_position_stop_loss(
            symbol="USDCHF",
            ticket=654,
            side="SELL",
            requested_stop=0.8080,
        )

        self.assertFalse(result.success)
        self.assertIn("nao melhora", " ".join(result.rejection_reasons))
        self.assertIsNone(mt5.last_request)

    def test_close_position_demo_usa_ordem_oposta(self) -> None:
        position = SimpleNamespace(
            ticket=987,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
            volume=0.1,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.tick = SimpleNamespace(ask=1.1042, bid=1.1040)
        provider = self._provider(mt5)

        result = provider.close_position(
            symbol="EURUSD",
            ticket=987,
            side="BUY",
            volume=0.1,
            reason="EARLY_EXIT_MOMENTUM_LOSS",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_DEAL)
        self.assertEqual(mt5.last_request["position"], 987)
        self.assertEqual(mt5.last_request["type"], mt5.ORDER_TYPE_SELL)
        self.assertEqual(mt5.last_request["volume"], 0.1)
        self.assertAlmostEqual(mt5.last_request["price"], 1.1040)
        self.assertEqual(mt5.last_request["comment"], "TraderIA PM EXIT")
        self.assertLessEqual(len(mt5.last_request["comment"]), 31)

    def test_close_position_conta_nao_demo_rejeita(self) -> None:
        position = SimpleNamespace(
            ticket=987,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
            volume=0.1,
        )
        mt5 = _FakeMT5(trade_mode=99, open_positions=[position])
        provider = self._provider(mt5)

        result = provider.close_position(
            symbol="EURUSD",
            ticket=987,
            side="BUY",
            volume=0.1,
            reason="EARLY_EXIT_MOMENTUM_LOSS",
        )

        self.assertFalse(result.accepted)
        self.assertIn("nao e demo", result.message)
        self.assertIsNone(mt5.last_request)

    def test_close_position_resposta_vazia_informa_last_error_e_order_check(self) -> None:
        position = SimpleNamespace(
            ticket=987,
            symbol="EURUSD",
            type=_FakeMT5.POSITION_TYPE_BUY,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
            volume=0.1,
        )
        mt5 = _FakeMT5(open_positions=[position])
        mt5.empty_order_response = True
        mt5.last_error_value = (10013, "Invalid request")
        provider = self._provider(mt5)

        result = provider.close_position(
            symbol="EURUSD",
            ticket=987,
            side="BUY",
            volume=0.1,
            reason="EARLY_EXIT_MOMENTUM_LOSS",
        )

        self.assertFalse(result.accepted)
        self.assertIn("resposta vazia", result.message)
        self.assertIn("Invalid request", result.message)
        self.assertIn("order_check=Done", result.message)

    def _provider(self, mt5: object) -> MT5DemoExecutionProvider:
        return MT5DemoExecutionProvider(
            mt5=mt5,
            log_path=Path(tempfile.gettempdir()) / "traderia-test-orders.jsonl",
            management_log_path=(
                Path(tempfile.gettempdir()) / "traderia-test-management.jsonl"
            ),
        )

    def _order(self) -> ExecutionOrder:
        return ExecutionOrder(
            symbol="WDO",
            side="BUY",
            quantity=0.1,
            entry_price=100.0,
            stop=90.0,
            target=120.0,
        )


class _FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 1
    ORDER_TYPE_SELL = 2
    ORDER_TIME_GTC = 3
    ORDER_FILLING_IOC = 4
    TRADE_ACTION_DEAL = 5
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_DONE = 10009
    TIMEFRAME_M1 = 1

    def __init__(self, trade_mode: int = 0, open_positions=None) -> None:
        self.trade_mode = trade_mode
        self.open_positions = open_positions
        self.last_request = None
        self.positions_symbol = None
        self.initialize_calls = 0
        self.tick = SimpleNamespace(ask=101.0, bid=99.0)
        self.rates = []
        self.empty_order_response = False
        self.last_error_value = (1, "Success")

    def initialize(self):
        self.initialize_calls += 1
        return True

    def account_info(self):
        return SimpleNamespace(trade_mode=self.trade_mode)

    def symbol_info(self, symbol: str):
        return SimpleNamespace(visible=True)

    def symbol_select(self, symbol: str, visible: bool):
        return True

    def symbol_info_tick(self, symbol: str):
        return self.tick

    def positions_get(self, symbol: str | None = None):
        self.positions_symbol = symbol
        return self.open_positions or []

    def copy_rates_from_pos(
        self,
        symbol: str,
        timeframe: int,
        start_pos: int,
        count: int,
    ):
        return self.rates

    def order_check(self, request: dict[str, object]):
        return SimpleNamespace(retcode=0, comment="Done")

    def last_error(self):
        return self.last_error_value

    def order_send(self, request: dict[str, object]):
        self.last_request = request
        if self.empty_order_response:
            return None
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            order=777,
            deal=888,
            price=request.get("price", 0.0),
            comment="done",
        )


class _AmbiguousRates:
    """Array-like que simula bool ambiguo do numpy/MetaTrader5."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def __bool__(self) -> bool:
        raise ValueError("truth value is ambiguous")


if __name__ == "__main__":
    unittest.main()
