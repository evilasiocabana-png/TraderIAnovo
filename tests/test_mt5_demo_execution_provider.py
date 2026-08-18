"""Testes do provider MT5 Demo sem conta real."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from application.model3_xau_m5_rsi50_flip import MODEL_3_ID
from application.model6_lab_forex_expansion import MODEL_6_ID
from application.forex_m5_sma_rsi_model_family import (
    MODEL_13_ID as FOREX_MODEL_13_ID,
    MODEL_14_ID as FOREX_MODEL_14_ID,
    MODEL_15_ID as FOREX_MODEL_15_ID,
)
from application.dynamic_exit_model_family import MODEL_8_ID as DYNAMIC_MODEL_8_ID
from application.model15_xau_m5_breakout import MODEL_15_ID
from application.model8_xau_m5_sma_rsi_reentry import MODEL_8_ID
from application.model23_basket_accumulator import model23_variant_id
from application.model24_xau_basket import model24_variant_id
from application.xau_m5_sma_rsi_model_family import MODEL_12_ID
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

    def test_novo_m8_envia_ordem_a_mercado_sem_tp(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.0,
                    stop=98.99,
                    target=0.0,
                    operational_model=MODEL_8_ID,
                    plan_snapshot={
                        "candle_time": "2026-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2026-08-10T20:00:00+00:00",
                    },
                )
            )
        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_DEAL)
        self.assertEqual(mt5.last_request["type"], mt5.ORDER_TYPE_BUY)
        self.assertEqual(mt5.last_request["tp"], 0.0)
        self.assertEqual(mt5.last_request["comment"], "TraderIA M8")

    def test_m3_retirado_nao_envia_ordem(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=3500.02, bid=3500.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=3500.0,
                    stop=3490.0,
                    target=0.0,
                    operational_model=MODEL_3_ID,
                    plan_snapshot={"candle_time": "2026-08-11T10:00:00+00:00"},
                )
            )
        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_reentrada_m8_envia_buy_stop_no_topo_anterior(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.50,
                    stop=110.0,
                    target=0.0,
                    operational_model=MODEL_8_ID,
                    plan_snapshot={
                        "candle_time": "2099-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                        "stop_management_parameters": {
                            "active_entry_order_type": "BUY_STOP",
                        },
                    },
                )
            )
        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(mt5.last_request["type"], mt5.ORDER_TYPE_BUY_STOP)
        self.assertEqual(mt5.last_request["price"], 120.50)
        self.assertEqual(mt5.last_request["tp"], 0.0)

    def test_m23_reentrada_xau_envia_tp_estrutural(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.50,
                    stop=110.0,
                    target=130.0,
                    operational_model=model23_variant_id(MODEL_8_ID),
                    plan_snapshot={
                        "candle_time": "2099-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                        "stop_management_parameters": {
                            "source_operational_model": MODEL_8_ID,
                            "active_entry_order_type": "BUY_STOP",
                            "m23_structural_target_enabled": True,
                            "m23_structural_target_price": 130.0,
                        },
                    },
                )
            )

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(mt5.last_request["price"], 120.50)
        self.assertEqual(mt5.last_request["tp"], 130.0)

    def test_expiracao_pendente_compara_relogio_do_servidor_mt5(self) -> None:
        provider = self._provider(_FakeMT5())
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=120.50,
            stop=110.0,
            target=0.0,
            operational_model=MODEL_8_ID,
            plan_snapshot={
                "candle_time": "1970-01-01T03:00:00+00:00",
                "stop_management_parameters": {
                    "active_entry_order_type": "BUY_STOP",
                },
            },
        )
        server_tick = SimpleNamespace(ask=120.02, bid=120.00, time=12_100)

        with patch("infrastructure.execution.mt5_demo_execution_provider.time.time", return_value=1_000):
            rejection = provider._stop_target_preflight(order, server_tick)

        self.assertIsNotNone(rejection)
        self.assertIn("expirou", rejection.message)

    def test_pendente_permanece_valida_durante_candle_seguinte(self) -> None:
        provider = self._provider(_FakeMT5())
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=120.50,
            stop=110.0,
            target=0.0,
            operational_model=MODEL_8_ID,
            plan_snapshot={
                "candle_time": "1970-01-01T03:05:00+00:00",
                "stop_management_parameters": {
                    "active_entry_order_type": "BUY_STOP",
                },
            },
        )
        server_tick = SimpleNamespace(ask=120.02, bid=120.00, time=11_101)

        rejection = provider._stop_target_preflight(order, server_tick)

        self.assertIsNone(rejection)
        self.assertEqual(provider._pending_stop_expiration(order), 11_700)

    def test_novo_candle_pode_atualizar_gatilho_da_mesma_reentrada(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )

            def order(candle_time: str, entry: float) -> ExecutionOrder:
                return ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=entry,
                    stop=110.0,
                    target=0.0,
                    operational_model=MODEL_8_ID,
                    plan_identity="XAUUSD|M5|M8|REENTRY_BUY",
                    plan_snapshot={
                        "candle_time": candle_time,
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": candle_time,
                        "stop_management_parameters": {
                            "active_entry_order_type": "BUY_STOP",
                        },
                    },
                )

            first = provider.submit_order(order("2099-08-10T20:00:00+00:00", 120.50))
            mt5.pending_orders = [
                SimpleNamespace(
                    ticket=81001,
                    symbol="XAUUSD",
                    type=mt5.ORDER_TYPE_BUY_STOP,
                    comment="TraderIA M8",
                )
            ]
            second = provider.submit_order(order("2099-08-10T20:05:00+00:00", 120.60))

        self.assertTrue(first.accepted)
        self.assertTrue(second.accepted)
        self.assertEqual(mt5.last_request["price"], 120.60)
        self.assertEqual(mt5.requests[-2]["action"], mt5.TRADE_ACTION_REMOVE)
        self.assertEqual(mt5.requests[-2]["order"], 81001)
        self.assertEqual(mt5.requests[-1]["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(
            mt5.requests[-1]["expiration"],
            int(datetime.fromisoformat("2099-08-10T20:15:00+00:00").timestamp()),
        )

    def test_modelo12_retirado_nao_envia_ordem(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.0,
                    stop=110.0,
                    target=0.0,
                    operational_model=MODEL_12_ID,
                    plan_snapshot={
                        "candle_time": "2026-08-10T20:05:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2026-08-10T20:05:00+00:00",
                    },
                )
            )
        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_modelo12_bloqueia_indicadores_recalculados_fora_do_mt5(self) -> None:
        mt5 = _FakeMT5()
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="XAUUSD",
                side="BUY",
                quantity=0.01,
                entry_price=120.0,
                stop=110.0,
                target=0.0,
                operational_model=MODEL_12_ID,
                plan_snapshot={"candle_time": "2026-08-10T20:05:00+00:00"},
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_m15_aposentado_nao_envia_buy_stop(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=2009.90, bid=2009.88)
        provider = self._provider(mt5)
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=2010.01,
            stop=2004.99,
            target=0.0,
            operational_model=MODEL_15_ID,
            plan_snapshot={"candle_time": "2099-08-06T13:00:00+00:00"},
        )

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_m15_aposentado_bloqueia_antes_de_avaliar_rompimento(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=2010.02, bid=2010.00)
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="XAUUSD",
                side="BUY",
                quantity=0.01,
                entry_price=2010.01,
                stop=2004.99,
                target=0.0,
                operational_model=MODEL_15_ID,
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_m15_aposentado_nao_substitui_pendencia_anterior(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=2009.90, bid=2009.88)
        mt5.pending_orders = [
            SimpleNamespace(
                ticket=15001,
                symbol="XAUUSD",
                type=mt5.ORDER_TYPE_BUY_STOP,
                comment="TraderIA M15",
            )
        ]
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="XAUUSD",
                side="BUY",
                quantity=0.01,
                entry_price=2010.01,
                stop=2004.99,
                target=0.0,
                operational_model=MODEL_15_ID,
                plan_snapshot={"candle_time": "2099-08-06T13:00:00+00:00"},
            )
        )

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertEqual(mt5.requests, [])

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

    def test_rejeita_sell_quando_ask_ja_encostou_no_stop(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=0.58408, bid=0.58349)
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="NZDUSD",
                side="SELL",
                quantity=0.1,
                entry_price=0.58349,
                stop=0.58407349,
                target=0.58232302,
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("stale", result.message)
        self.assertIn("ask", result.message)
        self.assertIsNone(mt5.last_request)

    def test_rejeita_preflight_quando_sl_tp_violam_distancia_minima_broker(
        self,
    ) -> None:
        mt5 = _FakeMT5()
        mt5.symbol = SimpleNamespace(
            visible=True,
            point=0.00001,
            trade_stops_level=50,
            trade_freeze_level=0,
        )
        mt5.tick = SimpleNamespace(ask=1.10000, bid=1.09998)
        provider = self._provider(mt5)

        result = provider.submit_order(
            ExecutionOrder(
                symbol="EURUSD",
                side="BUY",
                quantity=0.1,
                entry_price=1.10000,
                stop=1.09970,
                target=1.10040,
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("distancia minima do broker", result.message)
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

    def test_bloqueia_plano_identico_de_modelos_diferentes_no_mesmo_candle(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.10002, bid=1.10000)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            common = {
                "symbol": "EURUSD",
                "side": "BUY",
                "quantity": 0.1,
                "entry_price": 1.10001,
                "stop": 1.09800,
                "target": 1.10403,
                "plan_snapshot": {
                    "candle_time": "2026-07-22T11:30:00+00:00",
                },
            }
            first = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity="EURUSD|H1|M1|ALPHA_X",
                    operational_model="MODELO_1_ALPHA_ATUAL",
                )
            )
            second = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity="EURUSD|M30|M5|ALPHA_X",
                    operational_model="MODELO_5_LAB_CONSOLIDADO",
                )
            )

            self.assertTrue(first.accepted)
            self.assertFalse(second.accepted)
            self.assertIn("duplicado", second.message)

    def test_m23_e_modelo_fonte_podem_executar_o_mesmo_sinal(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.10002, bid=1.10000)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            common = {
                "symbol": "EURUSD",
                "side": "BUY",
                "quantity": 0.1,
                "entry_price": 1.10001,
                "stop": 1.09800,
                "target": 1.10403,
                "plan_identity": "EURUSD|H1|M1|ALPHA_X",
                "plan_snapshot": {
                    "candle_time": "2026-07-22T11:30:00+00:00",
                },
            }
            source = provider.submit_order(
                ExecutionOrder(
                    **common,
                    operational_model="MODELO_1_ALPHA_ATUAL",
                )
            )
            basket = provider.submit_order(
                ExecutionOrder(
                    **common,
                    operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M1",
                )
            )

            self.assertTrue(source.accepted)
            self.assertTrue(basket.accepted)
            self.assertEqual(len(mt5.requests), 2)

    def test_m8_ativo_e_m12_retirado_nao_abrem_juntos(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=4359.20, bid=4359.10)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            candle = datetime.now(timezone.utc).replace(
                second=0,
                microsecond=0,
            ).isoformat()
            common = {
                "symbol": "XAUUSD",
                "side": "SELL",
                "quantity": 0.1,
                "entry_price": 4359.18,
                "stop": 4366.07,
                "target": 0.0,
                "plan_snapshot": {
                    "candle_time": candle,
                    "indicator_source": "MT5_NATIVE",
                    "indicator_closed_candle_time": candle,
                },
            }

            first = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity=f"XAUUSD|M5|M8|{candle}",
                    operational_model=MODEL_8_ID,
                )
            )
            second = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity=f"XAUUSD|M5|M12|{candle}",
                    operational_model=MODEL_12_ID,
                )
            )

            self.assertTrue(first.accepted)
            self.assertFalse(second.accepted)
            self.assertIn("aposentado", second.message)

    def test_m8_aposentado_nao_compete_com_m1_no_mesmo_candle(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=1.10002, bid=1.10000)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            common = {
                "symbol": "EURUSD",
                "side": "BUY",
                "quantity": 0.1,
                "entry_price": 1.10001,
                "stop": 1.09800,
                "target": 1.10403,
                "plan_snapshot": {
                    "candle_time": "2026-08-05T11:30:00+00:00",
                },
            }
            fixed = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity="EURUSD|H1|M1|ALPHA013",
                    operational_model="MODELO_1_ALPHA_ATUAL",
                )
            )
            dynamic = provider.submit_order(
                ExecutionOrder(
                    **common,
                    plan_identity="EURUSD|H1|M8|ALPHA013",
                    operational_model=DYNAMIC_MODEL_8_ID,
                )
            )

            self.assertTrue(fixed.accepted)
            self.assertFalse(dynamic.accepted)
            self.assertIn("aposentado", dynamic.message)
            self.assertEqual(mt5.last_request["comment"], "TraderIA M1")

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

    def test_cache_do_historico_preserva_duplicidade_sem_snapshot_pesado(self) -> None:
        mt5 = _FakeMT5()
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "orders.jsonl"
            log_path.write_text(
                (
                    '{"symbol":"EURUSD","side":"BUY","entry_price":1.1,'
                    '"stop":1.09,"target":1.12,"accepted":true,'
                    '"plan_identity":"EURUSD|H1|M1|ALPHA013",'
                    '"operational_model":"MODELO_1_ALPHA_ATUAL",'
                    '"plan_snapshot":{"candle_time":"2026-08-12T19:00:00+00:00",'
                    '"operational_model":"MODELO_1_ALPHA_ATUAL",'
                    '"heavy_evidence":"nao deve ficar no cache",'
                    '"stop_management_parameters":'
                    '{"active_entry_order_type":"MARKET",'
                    '"heavy_indicators":[1,2,3]}}}\n'
                ),
                encoding="utf-8",
            )
            provider = MT5DemoExecutionProvider(mt5=mt5, log_path=log_path)

            records = provider._read_execution_log_records()

            self.assertEqual(len(records), 1)
            snapshot = records[0]["plan_snapshot"]
            self.assertNotIn("heavy_evidence", snapshot)
            self.assertNotIn(
                "heavy_indicators",
                snapshot["stop_management_parameters"],
            )
            self.assertEqual(
                snapshot["stop_management_parameters"]["active_entry_order_type"],
                "MARKET",
            )

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

    def test_posicao_manual_no_simbolo_bloqueia_ordem_automatica(self) -> None:
        position = SimpleNamespace(comment="manual")
        mt5 = _FakeMT5(open_positions=[position])
        provider = self._provider(mt5)

        self.assertTrue(
            provider.has_open_position_for_model("XAUUSD", MODEL_8_ID)
        )

    def test_has_open_position_for_model_permite_terceiro_modelo_no_par(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
            ]
        )
        provider = self._provider(mt5)

        self.assertTrue(
            provider.has_open_position_for_model("EURUSD", "MODELO_1_ALPHA_ATUAL")
        )
        self.assertTrue(
            provider.has_open_position_for_model(
                "EURUSD",
                "MODELO_2_ESPELHO_BETA2_RR1",
            )
        )
        self.assertFalse(
            provider.has_open_position_for_model("EURUSD", MODEL_3_ID)
        )
        self.assertFalse(
            provider.has_open_position_for_model("EURUSD", "MODELO_4_ESPELHO_M1")
        )
        self.assertFalse(
            provider.has_open_position_for_model("EURUSD", "MODELO_5_PRICE_ACTION")
        )
        self.assertFalse(
            provider.has_open_position_for_model("EURUSD", "MODELO_6_ESPELHO_M5")
        )
        self.assertFalse(
            provider.has_open_position_for_model(
                "EURUSD",
                "MODELO_7_TREND_MOMENTUM_DYNAMIC",
            )
        )

    def test_submit_order_bloqueia_m3_retirado(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(order, "operational_model", MODEL_3_ID)

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_submit_order_bloqueia_m4_retirado(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
                SimpleNamespace(comment="TraderIA M3"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(order, "operational_model", "MODELO_4_ESPELHO_M1")

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_provider_bloqueia_m6_e_m13_m15_retirados(self) -> None:
        for model_id in (
            MODEL_6_ID,
            FOREX_MODEL_13_ID,
            FOREX_MODEL_14_ID,
            FOREX_MODEL_15_ID,
        ):
            mt5 = _FakeMT5()
            provider = self._provider(mt5)
            order = self._order()
            object.__setattr__(order, "operational_model", model_id)

            result = provider.submit_order(order)

            self.assertFalse(result.accepted, model_id)
            self.assertIn("aposentado", result.message)
            self.assertIsNone(mt5.last_request)

    def test_submit_order_permite_quinta_posicao_m5_no_par(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
                SimpleNamespace(comment="TraderIA M3"),
                SimpleNamespace(comment="TraderIA M4"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(order, "operational_model", "MODELO_5_PRICE_ACTION")

        result = provider.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertIsNotNone(mt5.last_request)

    def test_submit_order_bloqueia_modelo6_aposentado(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
                SimpleNamespace(comment="TraderIA M3"),
                SimpleNamespace(comment="TraderIA M4"),
                SimpleNamespace(comment="TraderIA M5"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(
            order,
            "operational_model",
            "MODELO_6_TREND_MOMENTUM_ORIGINAL",
        )

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_submit_order_bloqueia_modelo7_aposentado(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
                SimpleNamespace(comment="TraderIA M3"),
                SimpleNamespace(comment="TraderIA M4"),
                SimpleNamespace(comment="TraderIA M5"),
                SimpleNamespace(comment="TraderIA M6"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(
            order,
            "operational_model",
            "MODELO_7_TREND_MOMENTUM_DYNAMIC",
        )

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_submit_order_bloqueia_modelo8_aposentado(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment="TraderIA M1"),
                SimpleNamespace(comment="TraderIA M2"),
                SimpleNamespace(comment="TraderIA M3"),
                SimpleNamespace(comment="TraderIA M4"),
                SimpleNamespace(comment="TraderIA M5"),
                SimpleNamespace(comment="TraderIA M6"),
                SimpleNamespace(comment="TraderIA M7"),
            ]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(
            order,
            "operational_model",
            "MODELO_8_TREND_PULLBACK_H1_M5",
        )

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_comments_identify_m8_to_m22_independently(self) -> None:
        provider = self._provider(_FakeMT5())

        self.assertEqual(provider._model_comment("MODELO_8_TREND_PULLBACK_H1_M5"), "M8")
        self.assertEqual(provider._model_comment("MODELO_9_TREND_PULLBACK_M15_M1"), "M9")
        self.assertEqual(provider._model_comment("MODELO_10_TREND_PULLBACK_D1_M15"), "M10")
        self.assertEqual(provider._model_comment("MODELO_11_ALPHA001_TREND_MOMENTUM"), "M11")
        self.assertEqual(provider._model_comment("MODELO_20_ALPHA016_REVERSAL"), "M20")
        self.assertEqual(provider._model_comment("MODELO_21_ESPELHO_M19"), "M21")
        self.assertEqual(provider._model_comment("MODELO_22_ESPELHO_M9"), "M22")

    def test_m23_envia_entrada_a_mercado_com_sl_tp_da_fonte(self) -> None:
        mt5 = _FakeMT5()
        provider = self._provider(mt5)
        source_model = "MODELO_1_ALPHA_ATUAL"
        order = self._order()
        object.__setattr__(order, "operational_model", model23_variant_id(source_model))
        object.__setattr__(
            order,
            "plan_snapshot",
            {
                "stop_management_parameters": {
                    "source_operational_model": source_model,
                }
            },
        )

        result = provider.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_DEAL)
        self.assertEqual(mt5.last_request["sl"], order.stop)
        self.assertEqual(mt5.last_request["tp"], order.target)
        self.assertEqual(mt5.last_request["comment"], "TraderIA M23 S1")

    def test_m23_preserva_ordem_pendente_e_sem_tp_da_fonte_m8(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        provider = self._provider(mt5)
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=120.50,
            stop=110.0,
            target=0.0,
            operational_model=model23_variant_id(MODEL_8_ID),
            plan_snapshot={
                "candle_time": "2099-08-10T20:00:00+00:00",
                "indicator_source": "MT5_NATIVE",
                "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                "stop_management_parameters": {
                    "source_operational_model": MODEL_8_ID,
                    "active_entry_order_type": "BUY_STOP",
                },
            },
        )

        result = provider.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(mt5.last_request["type"], mt5.ORDER_TYPE_BUY_STOP)
        self.assertEqual(mt5.last_request["sl"], 110.0)
        self.assertEqual(mt5.last_request["tp"], 0.0)
        self.assertEqual(mt5.last_request["comment"], "TraderIA M23 S8")

    def test_m24_reentrada_estrutural_envia_tp_individual(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.50,
                    stop=110.0,
                    target=130.0,
                    operational_model=model24_variant_id(
                        "MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75"
                    ),
                    plan_snapshot={
                        "candle_time": "2099-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                        "stop_management_parameters": {
                            "source_operational_model": (
                                "MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75"
                            ),
                            "active_entry_order_type": "BUY_STOP",
                            "indicator_source": "MT5_NATIVE",
                            "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                            "m24_individual_target_enabled": True,
                            "m24_entry_role": "REENTRY",
                        },
                    },
                )
            )
        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(mt5.last_request["tp"], 130.0)
        self.assertEqual(
            mt5.last_request["comment"],
            "TraderIA M24 S20 REENTRY",
        )

    def test_m24_reentrada_sell_envia_tp_no_fundo_estrutural(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="SELL",
                    quantity=0.01,
                    entry_price=119.50,
                    stop=130.0,
                    target=110.0,
                    operational_model=model24_variant_id(MODEL_8_ID),
                    plan_snapshot={
                        "candle_time": "2099-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                        "stop_management_parameters": {
                            "source_operational_model": MODEL_8_ID,
                            "active_entry_order_type": "SELL_STOP",
                            "m24_individual_target_enabled": True,
                            "m24_entry_role": "REENTRY",
                        },
                    },
                )
            )
        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(mt5.last_request["type"], mt5.ORDER_TYPE_SELL_STOP)
        self.assertEqual(mt5.last_request["tp"], 110.0)

    def test_m24_initial_preserva_tp_zero(self) -> None:
        mt5 = _FakeMT5()
        mt5.tick = SimpleNamespace(ask=120.02, bid=120.00)
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MT5DemoExecutionProvider(
                mt5=mt5,
                log_path=Path(temp_dir) / "orders.jsonl",
            )
            result = provider.submit_order(
                ExecutionOrder(
                    symbol="XAUUSD",
                    side="BUY",
                    quantity=0.01,
                    entry_price=120.02,
                    stop=110.0,
                    target=130.0,
                    operational_model=model24_variant_id(MODEL_8_ID),
                    plan_snapshot={
                        "candle_time": "2099-08-10T20:00:00+00:00",
                        "indicator_source": "MT5_NATIVE",
                        "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                        "stop_management_parameters": {
                            "source_operational_model": MODEL_8_ID,
                            "active_entry_order_type": "MARKET",
                            "m24_individual_target_enabled": False,
                            "m24_entry_role": "INITIAL",
                        },
                    },
                )
            )
        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_DEAL)
        self.assertEqual(mt5.last_request["tp"], 0.0)

    def test_m24_limita_uma_posicao_por_papel(self) -> None:
        open_initial = SimpleNamespace(
            ticket=24001,
            symbol="XAUUSD",
            comment="TraderIA M24 S8 INITIAL",
        )
        mt5 = _FakeMT5(open_positions=[open_initial])
        provider = self._provider(mt5)

        blocked = provider._open_position_model_limit_preflight(
            self._m24_order("INITIAL"),
        )
        allowed = provider._open_position_model_limit_preflight(
            self._m24_order("REENTRY"),
        )

        self.assertIsNotNone(blocked)
        self.assertIn("posicao inicial aberta", blocked.message)
        self.assertIsNone(allowed)

    def test_m24_limita_uma_reentrada_posicionada(self) -> None:
        open_reentry = SimpleNamespace(
            ticket=24002,
            symbol="XAUUSD",
            comment="TraderIA M24 S8 REENTRY",
        )
        provider = self._provider(_FakeMT5(open_positions=[open_reentry]))

        blocked = provider._open_position_model_limit_preflight(
            self._m24_order("REENTRY"),
        )

        self.assertIsNotNone(blocked)
        self.assertIn("posicao reentrada aberta", blocked.message)

    def test_m24_identifica_papel_de_posicao_legada_pelo_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "orders.jsonl"
            log_path.write_text(
                (
                    '{"accepted": true, "ticket": 24003, '
                    '"operational_model": "MODELO_24_XAU_RSI50_BASKET_SOURCE_M8", '
                    '"plan_snapshot": {"stop_management_parameters": '
                    '{"m24_entry_role": "INITIAL"}}}\n'
                ),
                encoding="utf-8",
            )
            position = SimpleNamespace(
                ticket=24003,
                symbol="XAUUSD",
                comment="TraderIA M24 S8",
            )
            provider = MT5DemoExecutionProvider(
                mt5=_FakeMT5(open_positions=[position]),
                log_path=log_path,
            )

            blocked = provider._open_position_model_limit_preflight(
                self._m24_order("INITIAL"),
            )

        self.assertIsNotNone(blocked)
        self.assertIn("posicao inicial aberta", blocked.message)

    def test_m24_bloqueia_initial_oposta_enquanto_reentry_esta_aberta(self) -> None:
        open_reentry = SimpleNamespace(
            ticket=24004,
            symbol="XAUUSD",
            comment="TraderIA M24 S8 REENTRY",
            type=_FakeMT5.POSITION_TYPE_BUY,
        )
        provider = self._provider(_FakeMT5(open_positions=[open_reentry]))

        blocked = provider._open_position_model_limit_preflight(
            self._m24_order("INITIAL", side="SELL"),
        )

        self.assertIsNotNone(blocked)
        self.assertIn("hedge M24 bloqueado", blocked.message)

    def test_m24_limita_reentrada_pendente_global_entre_fontes(self) -> None:
        pending = SimpleNamespace(
            ticket=24005,
            symbol="XAUUSD",
            comment="TraderIA M24 S8 REENTRY",
            type=_FakeMT5.ORDER_TYPE_BUY_STOP,
        )
        mt5 = _FakeMT5()
        mt5.pending_orders = [pending]
        provider = self._provider(mt5)

        blocked = provider._model24_pending_transition_preflight_locked(
            self._m24_order(
                "REENTRY",
                source_model="MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
            )
        )

        self.assertIsNotNone(blocked)
        self.assertIn("reentrada pendente global", blocked.message)

    def test_m24_initial_oposta_cancela_reentrada_pendente_anterior(self) -> None:
        pending = SimpleNamespace(
            ticket=24006,
            symbol="XAUUSD",
            comment="TraderIA M24 S8 REENTRY",
            type=_FakeMT5.ORDER_TYPE_BUY_STOP,
        )
        mt5 = _FakeMT5()
        mt5.pending_orders = [pending]
        provider = self._provider(mt5)

        blocked = provider._model24_pending_transition_preflight_locked(
            self._m24_order("INITIAL", side="SELL"),
        )

        self.assertIsNone(blocked)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_REMOVE)
        self.assertEqual(mt5.last_request["order"], 24006)

    def _m24_order(
        self,
        role: str,
        *,
        side: str = "BUY",
        source_model: str = MODEL_8_ID,
    ) -> ExecutionOrder:
        normalized_side = str(side).upper()
        return ExecutionOrder(
            symbol="XAUUSD",
            side=normalized_side,
            quantity=0.01,
            entry_price=120.0,
            stop=110.0 if normalized_side == "BUY" else 130.0,
            target=0.0,
            operational_model=model24_variant_id(source_model),
            plan_snapshot={
                "stop_management_parameters": {
                    "source_operational_model": source_model,
                    "active_entry_order_type": (
                        "MARKET"
                        if role == "INITIAL"
                        else f"{normalized_side}_STOP"
                    ),
                    "m24_entry_role": role,
                }
            },
        )

    def test_m23_nao_bloqueia_entrada_por_orcamento_financeiro_global(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(
                    comment="TraderIA M23 S8",
                    type=_FakeMT5.ORDER_TYPE_BUY,
                    symbol="XAUUSD",
                    volume=0.1,
                    price_open=120.0,
                    sl=100.0,
                )
            ]
        )
        mt5.profit_scale = 100.0
        mt5.tick = SimpleNamespace(ask=120.0, bid=119.9)
        provider = self._provider(mt5)
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.1,
            entry_price=120.0,
            stop=105.0,
            target=130.0,
            operational_model=model23_variant_id("MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR"),
            plan_snapshot={
                "candle_time": "2099-08-10T20:00:00+00:00",
                "indicator_source": "MT5_NATIVE",
                "indicator_closed_candle_time": "2099-08-10T20:00:00+00:00",
                "stop_management_parameters": {
                    "source_operational_model": "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
                }
            },
        )

        result = provider.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertIsNotNone(mt5.last_request)

    def test_m23_permite_reentrada_da_mesma_fonte_em_novo_sinal(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[SimpleNamespace(comment="TraderIA M23 S1")]
        )
        provider = self._provider(mt5)

        self.assertFalse(
            provider.has_open_position_for_model(
                "WDO",
                model23_variant_id("MODELO_1_ALPHA_ATUAL"),
            )
        )
        self.assertFalse(
            provider.has_open_position_for_model(
                "WDO",
                model23_variant_id("MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS"),
            )
        )
        order = self._order()
        object.__setattr__(
            order,
            "operational_model",
            model23_variant_id("MODELO_1_ALPHA_ATUAL"),
        )
        object.__setattr__(
            order,
            "plan_snapshot",
            {
                "candle_time": "2099-08-12T20:05:00+00:00",
                "stop_management_parameters": {
                    "source_operational_model": "MODELO_1_ALPHA_ATUAL",
                },
            },
        )

        result = provider.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["comment"], "TraderIA M23 S1")

    def test_submit_order_bloqueia_vigesima_terceira_posicao_no_par(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[
                SimpleNamespace(comment=f"TraderIA M{index}")
                for index in range(1, 23)
            ]
        )
        provider = self._provider(mt5)

        result = provider.submit_order(self._order())

        self.assertFalse(result.accepted)
        self.assertIn("Limite de vinte e duas posicoes por par", result.message)
        self.assertIsNone(mt5.last_request)

    def test_m21_aposentado_nao_abre_nova_ordem(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[SimpleNamespace(comment="TraderIA M19")]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(order, "operational_model", "MODELO_21_ESPELHO_M19")

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

    def test_m22_aposentado_nao_abre_nova_ordem(self) -> None:
        mt5 = _FakeMT5(
            open_positions=[SimpleNamespace(comment="TraderIA M9")]
        )
        provider = self._provider(mt5)
        order = self._order()
        object.__setattr__(order, "operational_model", "MODELO_22_ESPELHO_M9")

        result = provider.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("aposentado", result.message)
        self.assertIsNone(mt5.last_request)

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
            self.assertIn('"plan_snapshot"', content)

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

    def test_remove_tp_preserva_sl_da_posicao_demo(self) -> None:
        position = SimpleNamespace(
            ticket=2468,
            symbol="XAUUSD",
            type=_FakeMT5.POSITION_TYPE_SELL,
            price_open=4400.0,
            sl=4410.0,
            tp=4380.0,
            volume=0.1,
        )
        mt5 = _FakeMT5(open_positions=[position])
        provider = self._provider(mt5)

        result = provider.modify_position_tp("XAUUSD", 2468, 0.0)

        self.assertTrue(result.accepted)
        self.assertEqual(mt5.last_request["action"], mt5.TRADE_ACTION_SLTP)
        self.assertEqual(mt5.last_request["position"], 2468)
        self.assertEqual(mt5.last_request["sl"], 4410.0)
        self.assertEqual(mt5.last_request["tp"], 0.0)

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
            plan_snapshot={"alpha_id": "ALPHA999", "entry_setup": "TEST_SETUP"},
        )


class _FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 1
    ORDER_TYPE_SELL = 2
    ORDER_TYPE_BUY_STOP = 3
    ORDER_TYPE_SELL_STOP = 4
    ORDER_TIME_GTC = 3
    ORDER_TIME_SPECIFIED = 4
    ORDER_FILLING_IOC = 4
    ORDER_FILLING_RETURN = 5
    TRADE_ACTION_DEAL = 5
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_PENDING = 7
    TRADE_ACTION_REMOVE = 8
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
        self.symbol = SimpleNamespace(visible=True)
        self.pending_orders = []
        self.requests = []
        self.profit_scale = 1.0

    def initialize(self):
        self.initialize_calls += 1
        return True

    def account_info(self):
        return SimpleNamespace(trade_mode=self.trade_mode)

    def symbol_info(self, symbol: str):
        return self.symbol

    def symbol_select(self, symbol: str, visible: bool):
        return True

    def symbol_info_tick(self, symbol: str):
        return self.tick

    def positions_get(self, symbol: str | None = None):
        self.positions_symbol = symbol
        return self.open_positions or []

    def orders_get(self, symbol: str | None = None):
        return self.pending_orders

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

    def order_calc_profit(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ):
        del symbol
        direction = 1.0 if order_type == self.ORDER_TYPE_BUY else -1.0
        return (
            (float(price_close) - float(price_open))
            * direction
            * float(volume)
            * self.profit_scale
        )

    def last_error(self):
        return self.last_error_value

    def order_send(self, request: dict[str, object]):
        self.last_request = request
        self.requests.append(dict(request))
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
