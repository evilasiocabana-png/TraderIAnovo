from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.demo_execution_service import DemoExecutionService
from application.model8_xau_m5_sma_rsi_reentry import (
    load_model8_runtime_state,
    update_model8_runtime_state,
)
from application.xau_m5_sma_rsi_model_family import (
    MODEL_9_ID,
    MODEL_10_ID,
    MODEL_11_ID,
    MODEL_12_ID,
    MODEL_18_ID,
    MODEL_19_ID,
    MODEL_20_ID,
    MODEL_21_ID,
    MODEL_22_ID,
    XAU_IMPROVED_REENTRY_MODEL_IDS,
    XAU_REENTRY_TARGET_MODE,
    trend_filter_spec,
    xau_model_requires_target,
    xau_reentry_target,
    xau_trend_filter_parameters,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)
from infrastructure.execution.mt5_demo_execution_provider import (
    MT5DemoExecutionProvider,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from tests.test_model8_xau_m5_sma_rsi_reentry import _candles


class XAUImprovedReentryModelsTest(unittest.TestCase):
    @staticmethod
    def _fallback_plan() -> MT5ResearchTradePlan:
        return MT5ResearchTradePlan(
            symbol="XAUUSD",
            timeframe="M5",
            direction="WAIT",
            entry_price=None,
            stop=None,
            target=None,
            risk_reward=0.0,
            stop_multiplier=0.0,
            exit_model="NONE",
            exit_score=0.0,
            exit_candidates=0,
            status="SEM_PLANO",
        )

    @staticmethod
    def _service() -> DashboardService:
        rows = _candles(
            ([100.0] * 150) + ([98.0] * 49) + [120.0],
            pivot="low",
        )
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(
                latest_forex_candles={("XAUUSD", "M5"): rows},
                supplemental_forex_seed_only_keys=set(),
            ),
        )
        return service

    def test_mapeamento_preserva_as_cinco_origens(self) -> None:
        expected = {
            MODEL_18_ID: "MODELO_8_XAU_M5_SMA_RSI_REENTRY",
            MODEL_19_ID: MODEL_9_ID,
            MODEL_20_ID: MODEL_10_ID,
            MODEL_21_ID: MODEL_11_ID,
            MODEL_22_ID: MODEL_12_ID,
        }
        self.assertEqual(set(XAU_IMPROVED_REENTRY_MODEL_IDS), set(expected))
        for model_id, source_id in expected.items():
            spec = trend_filter_spec(model_id)
            self.assertIsNotNone(spec)
            self.assertEqual(spec.source_model_id, source_id)  # type: ignore[union-attr]
            self.assertEqual(spec.reentry_target_points, 0.0)  # type: ignore[union-attr]
            self.assertTrue(spec.reentry_structural_target)  # type: ignore[union-attr]
            self.assertIsNone(spec.max_reentries_per_signal)  # type: ignore[union-attr]
            self.assertTrue(is_active_operational_model(model_id))
            self.assertFalse(is_retired_operational_model(model_id))

    def test_parametros_documentam_tp_exclusivo_da_reentrada(self) -> None:
        for model_id in XAU_IMPROVED_REENTRY_MODEL_IDS:
            parameters = xau_trend_filter_parameters(model_id)
            self.assertFalse(parameters["initial_take_profit_enabled"])
            self.assertIsNone(parameters["reentry_take_profit_points"])
            self.assertEqual(parameters["reentry_take_profit_mode"], XAU_REENTRY_TARGET_MODE)
            self.assertEqual(parameters["pending_stop_validity"], "ONE_M5_CANDLE")
            self.assertIsNone(parameters["max_reentries_per_signal"])
            self.assertTrue(parameters["reentries_unlimited_while_trend_valid"])

    def test_alvo_so_existe_na_reentrada_buy_e_sell(self) -> None:
        self.assertEqual(
            xau_reentry_target(MODEL_18_ID, "BUY", 2500.0, "MARKET", 2600.0),
            0.0,
        )
        self.assertEqual(
            xau_reentry_target(MODEL_18_ID, "BUY", 2500.0, "BUY_STOP", 2600.0),
            2600.0,
        )
        self.assertEqual(
            xau_reentry_target(MODEL_18_ID, "SELL", 2500.0, "SELL_STOP", 2400.0),
            2400.0,
        )

    def test_servico_demo_exige_tp_na_reentrada_melhorada(self) -> None:
        snapshot = {
            "stop_management_parameters": {"active_entry_order_type": "BUY_STOP"}
        }
        valid = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=2500.0,
            stop=2490.0,
            target=2600.0,
            operational_model=MODEL_18_ID,
            plan_snapshot=snapshot,
        )
        missing_target = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=2500.0,
            stop=2490.0,
            target=0.0,
            operational_model=MODEL_18_ID,
            plan_snapshot=snapshot,
        )
        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(valid))
        self.assertFalse(
            DemoExecutionService()._has_required_stop_and_target(missing_target)
        )
        self.assertTrue(xau_model_requires_target(MODEL_18_ID, "BUY_STOP"))
        self.assertFalse(xau_model_requires_target(MODEL_18_ID, "MARKET"))

    def test_provider_envia_tp_na_ordem_buy_stop_da_reentrada(self) -> None:
        mt5 = SimpleNamespace(
            ORDER_TYPE_BUY_STOP=4,
            ORDER_TYPE_SELL_STOP=5,
            TRADE_ACTION_PENDING=5,
            ORDER_TIME_GTC=0,
            ORDER_FILLING_RETURN=2,
            ORDER_FILLING_IOC=1,
        )
        provider = MT5DemoExecutionProvider(mt5=mt5)
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=2500.0,
            stop=2490.0,
            target=2600.0,
            operational_model=MODEL_18_ID,
            plan_snapshot={
                "stop_management_parameters": {
                    "active_entry_order_type": "BUY_STOP"
                }
            },
        )
        request = provider._request(order, SimpleNamespace(ask=2499.0, bid=2498.5))
        self.assertEqual(request["action"], mt5.TRADE_ACTION_PENDING)
        self.assertEqual(request["type"], mt5.ORDER_TYPE_BUY_STOP)
        self.assertEqual(request["tp"], 2600.0)

    def test_dashboard_m18_inicial_sem_tp_e_reentrada_com_alvo_estrutural(self) -> None:
        service = self._service()
        row = DashboardMT5ForexSignalRowViewModel(pair="XAUUSD")
        with patch(
            "application.dashboard_service.load_model8_runtime_state",
            return_value={},
        ), patch(
            "application.dashboard_service.update_model8_runtime_state",
            return_value={"signal_cycle_side": "BUY"},
        ):
            _initial_row, initial = service._mt5_xau_trend_filter_plan(
                row,
                self._fallback_plan(),
                MODEL_18_ID,
            )
        self.assertEqual(initial.status, "PLANO_VALIDO")
        self.assertEqual(initial.target, 0.0)

        service.mt5_market_data_service.latest_forex_candles[("XAUUSD", "M5")] = (
            _candles(
                [100.0 + (index * 0.2) for index in range(58)] + [112.0, 111.0],
                pivot="low",
            )
        )

        with patch(
            "application.dashboard_service.load_model8_runtime_state",
            return_value={
                "signal_cycle_side": "BUY",
                "initial_entry_consumed": True,
                "reentry_consumed": False,
                "entry_intent_side": "BUY",
            },
        ):
            reentry_row, reentry = service._mt5_xau_trend_filter_plan(
                row,
                self._fallback_plan(),
                MODEL_18_ID,
            )
        self.assertEqual(reentry_row.theoretical_entry_status, "ORDEM_STOP_TEORICA")
        self.assertGreater(float(reentry.target or 0.0), float(reentry.entry_price or 0.0))
        self.assertEqual(
            reentry.target,
            reentry.stop_management_parameters["structural_target_price"],
        )
        self.assertGreater(reentry.risk_reward, 0.0)

    def test_estado_de_ciclo_isola_m18_e_m22(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            m18 = Path(directory) / "m18.json"
            m22 = Path(directory) / "m22.json"
            update_model8_runtime_state(
                path=m18,
                operational_model=MODEL_18_ID,
                signal_cycle_side="BUY",
                initial_entry_consumed=True,
                reentry_consumed=False,
            )
            update_model8_runtime_state(
                path=m22,
                operational_model=MODEL_22_ID,
                signal_cycle_side="SELL",
                initial_entry_consumed=True,
                reentry_consumed=True,
            )
            self.assertFalse(load_model8_runtime_state(m18)["reentry_consumed"])
            self.assertTrue(load_model8_runtime_state(m22)["reentry_consumed"])

    def test_reentrada_consumida_nao_bloqueia_novo_recuo_valido(self) -> None:
        service = self._service()
        service.mt5_market_data_service.latest_forex_candles[("XAUUSD", "M5")] = (
            _candles(
                [100.0 + (index * 0.2) for index in range(58)] + [112.0, 111.0],
                pivot="low",
            )
        )
        with patch(
            "application.dashboard_service.load_model8_runtime_state",
            return_value={
                "signal_cycle_side": "BUY",
                "initial_entry_consumed": True,
                "reentry_consumed": True,
                "entry_intent_side": "BUY",
            },
        ):
            decision = service.get_xau_trend_filter_entry_decision(MODEL_18_ID)

        self.assertTrue(decision.ready)
        self.assertEqual(decision.base.signal_kind, "REENTRY")
        self.assertEqual(decision.base.entry_order_type, "BUY_STOP")


if __name__ == "__main__":
    unittest.main()
