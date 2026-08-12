from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.demo_execution_service import DemoExecutionService
from application.forex_m5_sma_rsi_model_family import (
    FOREX_SMA_RSI_PAIRS,
    MODEL_13_ID,
    MODEL_14_ID,
    MODEL_15_ID,
    MODEL_16_ID,
    MODEL_17_ID,
    evaluate_forex_sma_rsi_entry,
    forex_pip_size,
    forex_sma_rsi_parameters,
    update_forex_sma_rsi_runtime_state,
)
from tests.test_model8_xau_m5_sma_rsi_reentry import _candles
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import is_active_operational_model
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _strong_buy() -> list[dict[str, float | str]]:
    return _candles([100.0 + (index * 0.2) for index in range(60)], pivot="low")


class ForexM5SmaRsiModelFamilyTest(unittest.TestCase):
    def test_m13_setup_a_cobre_exatamente_os_17_pares(self) -> None:
        self.assertEqual(len(FOREX_SMA_RSI_PAIRS), 17)
        for pair in FOREX_SMA_RSI_PAIRS:
            decision = evaluate_forex_sma_rsi_entry(MODEL_13_ID, pair, _strong_buy())
            self.assertTrue(decision.ready, pair)
            self.assertEqual(decision.base.direction, "BUY")
            self.assertEqual(decision.setup, "A")

    def test_m13_usa_um_pip_compativel_com_o_par(self) -> None:
        self.assertEqual(forex_pip_size("EURUSD"), 0.0001)
        self.assertEqual(forex_pip_size("USDJPY"), 0.01)
        self.assertEqual(
            forex_sma_rsi_parameters(MODEL_13_ID, "EURUSD")["setup"],
            "A",
        )

    def test_m13_bloqueia_ativo_fora_do_forex_oficial(self) -> None:
        decision = evaluate_forex_sma_rsi_entry(MODEL_13_ID, "XAUUSD", _strong_buy())
        self.assertFalse(decision.ready)
        self.assertIn("OUTSIDE_MODEL_SCOPE", decision.status)

    def test_m14_setup_b_exige_adx_acima_de_25(self) -> None:
        decision = evaluate_forex_sma_rsi_entry(MODEL_14_ID, "EURUSD", _strong_buy())
        self.assertTrue(decision.ready)
        self.assertGreater(decision.adx14 or 0.0, 25.0)
        self.assertEqual(decision.passed_filters, ("ADX14>25",))

        flat = _candles([100.0] * 60, pivot="low")
        blocked = evaluate_forex_sma_rsi_entry(MODEL_14_ID, "EURUSD", flat)
        self.assertFalse(blocked.ready)
        self.assertIn("ADX", blocked.status)

    def test_m15_setup_c_exige_distancia_sma_normalizada_por_atr(self) -> None:
        decision = evaluate_forex_sma_rsi_entry(MODEL_15_ID, "GBPUSD", _strong_buy())
        self.assertTrue(decision.ready)
        self.assertGreaterEqual(decision.distance_atr or 0.0, 0.25)
        self.assertEqual(decision.passed_filters, ("DISTANCE_ATR>=0.25",))

    def test_m16_setup_d_exige_inclinacao_direcional_da_sma50(self) -> None:
        decision = evaluate_forex_sma_rsi_entry(MODEL_16_ID, "USDCAD", _strong_buy())
        self.assertTrue(decision.ready)
        self.assertGreaterEqual(decision.sma50_slope_atr or 0.0, 0.05)
        self.assertEqual(decision.passed_filters, ("SMA50_SLOPE_ATR>=0.05",))

    def test_m17_setup_e_exige_os_tres_filtros(self) -> None:
        decision = evaluate_forex_sma_rsi_entry(MODEL_17_ID, "EURJPY", _strong_buy())
        self.assertTrue(decision.ready)
        self.assertEqual(
            decision.passed_filters,
            ("ADX14>25", "DISTANCE_ATR>=0.25", "SMA50_SLOPE_ATR>=0.05"),
        )
        self.assertEqual(decision.failed_filters, ())

    def test_m13_a_m17_possuem_identidades_ativas(self) -> None:
        for model_id in (MODEL_13_ID, MODEL_14_ID, MODEL_15_ID, MODEL_16_ID, MODEL_17_ID):
            self.assertTrue(is_active_operational_model(model_id), model_id)

    def test_estado_de_reentrada_forex_persiste_o_par_correto(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "model13_EURNZD_runtime_state.json"
            with patch(
                "application.forex_m5_sma_rsi_model_family.forex_runtime_state_path",
                return_value=target,
            ):
                state = update_forex_sma_rsi_runtime_state(
                    MODEL_13_ID,
                    "EURNZD",
                    entry_intent_side="BUY",
                )

        self.assertEqual(state["symbol"], "EURNZD")
        self.assertEqual(state["operational_model"], MODEL_13_ID)

    def test_dashboard_materializa_m17_com_trade_plan_proprio(self) -> None:
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(latest_forex_candles={("EURUSD", "M5"): _strong_buy()}),
        )
        fallback = MT5ResearchTradePlan(
            symbol="EURUSD", timeframe="M5", direction="WAIT", entry_price=None,
            stop=None, target=None, risk_reward=0.0, stop_multiplier=0.0,
            exit_model="NONE", exit_score=0.0, exit_candidates=0, status="SEM_PLANO",
        )
        with patch(
            "application.dashboard_service.load_forex_sma_rsi_runtime_state",
            return_value={},
        ):
            row, plan = service._mt5_forex_sma_rsi_plan(
                DashboardMT5ForexSignalRowViewModel(pair="EURUSD"),
                fallback,
                MODEL_17_ID,
            )
        self.assertEqual(row.decision, "BUY")
        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.source, "MODEL_17_FOREX_MANUAL_RULE")
        self.assertEqual(plan.target, 0.0)

    def test_execucao_m15_forex_aceita_plano_sem_tp(self) -> None:
        order = ExecutionOrder(
            symbol="GBPUSD", side="BUY", quantity=0.01,
            entry_price=1.25, stop=1.24, target=0.0,
            operational_model=MODEL_15_ID,
        )
        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(order))


if __name__ == "__main__":
    unittest.main()
