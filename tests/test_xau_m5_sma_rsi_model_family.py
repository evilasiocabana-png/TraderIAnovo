from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.demo_execution_service import DemoExecutionService
from application.mt5_demo_robot_service import (
    MT5DemoRobotService,
    MT5DemoRobotSignal,
    MT5DemoTradePlan,
)
from application.mt5_market_data_service import MT5MarketDataService
from application.position_manager_service import PositionManagerService, PositionTradePlan
from application.xau_m5_sma_rsi_model_family import (
    MODEL_9_ID,
    MODEL_10_ID,
    MODEL_11_ID,
    MODEL_12_ID,
    XAU_TREND_FILTER_MODEL_IDS,
    evaluate_xau_trend_filter_entry,
    trend_filter_spec,
    xau_trend_filter_parameters,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from tests.test_model8_xau_m5_sma_rsi_reentry import _candles


def _strong_buy_cross() -> list[dict[str, float | str]]:
    closes = [100.0 + (index * 0.2) for index in range(80)]
    peak = closes[-1]
    closes.extend((peak - 2.0, peak - 4.0, peak + 4.0))
    return _candles(closes, pivot="low")


class XAUTrendFilterModelFamilyTest(unittest.TestCase):
    def test_modelos_exibem_filtros_diferentes_sem_exigir_cruzamento_rsi(self) -> None:
        rows = _candles([100.0 + (index * 0.2) for index in range(60)], pivot="low")
        decisions = {
            model_id: evaluate_xau_trend_filter_entry(model_id, rows)
            for model_id in XAU_TREND_FILTER_MODEL_IDS
        }
        self.assertIn("ADX", decisions[MODEL_9_ID].status)
        self.assertIn("DISTANCIA_ATR", decisions[MODEL_10_ID].status)
        self.assertIn("INCLINACAO_SMA50", decisions[MODEL_11_ID].status)
        self.assertIn("FILTROS_COMBINADOS", decisions[MODEL_12_ID].status)
        self.assertEqual(len({decision.status for decision in decisions.values()}), 4)

    def test_cache_primario_curto_recebe_aquecimento_minimo_de_52_candles(self) -> None:
        service = MT5MarketDataService.__new__(MT5MarketDataService)
        service.latest_forex_signal_dashboard = SimpleNamespace(
            pairs=[SimpleNamespace(pair="XAUUSD", timeframe="M5")]
        )
        service.latest_forex_candles = {("XAUUSD", "M5"): [object()] * 51}
        service.supplemental_forex_refresh_started = {}
        service._read_supplemental_forex_batch = Mock(return_value={})

        service.refresh_supplemental_forex_candles(
            {"XAUUSD": {"M5"}},
            full_count=52,
        )

        service._read_supplemental_forex_batch.assert_called_once_with(
            {"M5": {"XAUUSD"}},
            count=52,
        )

    def test_status_de_aquecimento_mostra_recebidos_e_exigidos(self) -> None:
        decision = evaluate_xau_trend_filter_entry(MODEL_12_ID, [object()] * 51)
        self.assertEqual(decision.status, "M12_AQUECENDO_51_DE_52_CANDLES")
        self.assertIn("recebeu 51 de 52", decision.reason)

    def test_identidades_novas_sao_ativas_e_legados_continuam_aposentados(self) -> None:
        self.assertEqual(
            XAU_TREND_FILTER_MODEL_IDS,
            (MODEL_9_ID, MODEL_10_ID, MODEL_11_ID, MODEL_12_ID),
        )
        for model_id in XAU_TREND_FILTER_MODEL_IDS:
            self.assertTrue(is_active_operational_model(model_id))
            self.assertFalse(is_retired_operational_model(model_id))
        self.assertTrue(is_retired_operational_model("MODELO_9_DYNAMIC_EXIT_FROM_M2"))
        self.assertTrue(is_retired_operational_model("MODELO_10_TREND_PULLBACK_D1_M15"))

    def test_setup_b_exige_adx_acima_de_25(self) -> None:
        decision = evaluate_xau_trend_filter_entry(MODEL_9_ID, _strong_buy_cross())
        self.assertTrue(decision.ready)
        self.assertGreater(decision.adx14 or 0.0, 25.0)
        self.assertEqual(decision.passed_filters, ("ADX14>25",))

    def test_setup_c_exige_distancia_normalizada_por_atr(self) -> None:
        decision = evaluate_xau_trend_filter_entry(MODEL_10_ID, _strong_buy_cross())
        self.assertTrue(decision.ready)
        self.assertGreaterEqual(decision.distance_atr or 0.0, 0.25)

    def test_setup_d_exige_inclinacao_sma50_na_direcao(self) -> None:
        decision = evaluate_xau_trend_filter_entry(MODEL_11_ID, _strong_buy_cross())
        self.assertTrue(decision.ready)
        self.assertGreaterEqual(decision.sma50_slope_atr or 0.0, 0.05)

    def test_setup_e_exige_os_tres_filtros(self) -> None:
        decision = evaluate_xau_trend_filter_entry(MODEL_12_ID, _strong_buy_cross())
        self.assertTrue(decision.ready)
        self.assertEqual(len(decision.passed_filters), 3)
        self.assertEqual(decision.failed_filters, ())

    def test_setup_e_herda_reentrada_buy_stop_do_modelo_base(self) -> None:
        decision = evaluate_xau_trend_filter_entry(
            MODEL_12_ID,
            _strong_buy_cross(),
            awaiting_reentry_side="BUY",
        )
        self.assertTrue(decision.ready)
        self.assertEqual(decision.base.signal_kind, "REENTRY")
        self.assertEqual(decision.base.entry_order_type, "BUY_STOP")

    def test_parametros_ficam_congelados_por_modelo(self) -> None:
        self.assertEqual(xau_trend_filter_parameters(MODEL_9_ID)["adx_min_exclusive"], 25.0)
        self.assertEqual(xau_trend_filter_parameters(MODEL_10_ID)["distance_atr_min"], 0.25)
        self.assertEqual(xau_trend_filter_parameters(MODEL_11_ID)["sma50_slope_lookback"], 1)
        self.assertEqual(xau_trend_filter_parameters(MODEL_12_ID)["sma50_slope_atr_min"], 0.05)

    def test_dashboard_materializa_setup_e_com_identidade_propria(self) -> None:
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): _strong_buy_cross()}),
        )
        fallback = MT5ResearchTradePlan(
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
        with patch("application.dashboard_service.load_model8_runtime_state", return_value={}):
            row, plan = service._mt5_xau_trend_filter_plan(
                DashboardMT5ForexSignalRowViewModel(pair="XAUUSD"),
                fallback,
                MODEL_12_ID,
            )
        spec = trend_filter_spec(MODEL_12_ID)
        self.assertIsNotNone(spec)
        self.assertEqual(row.decision, "BUY")
        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.source, "MODEL_12_MANUAL_RULE")
        self.assertEqual(plan.alpha_id, spec.alpha_id)  # type: ignore[union-attr]
        self.assertEqual(plan.target, 0.0)

    def test_dashboard_materializa_reentrada_setup_e_com_buy_stop(self) -> None:
        candles = _strong_buy_cross()
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): candles}),
        )
        fallback = MT5ResearchTradePlan(
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
        with patch(
            "application.dashboard_service.load_model8_runtime_state",
            return_value={"entry_intent_side": "BUY"},
        ):
            row, plan = service._mt5_xau_trend_filter_plan(
                DashboardMT5ForexSignalRowViewModel(pair="XAUUSD"),
                fallback,
                MODEL_12_ID,
            )
        self.assertEqual(row.theoretical_entry_status, "ORDEM_STOP_TEORICA")
        self.assertEqual(
            plan.stop_management_parameters["active_entry_order_type"],
            "BUY_STOP",
        )
        self.assertEqual(plan.entry_price, row.theoretical_entry_price)

    def test_execucao_e_robo_aceitam_modelo_sem_tp(self) -> None:
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=120.0,
            stop=110.0,
            target=0.0,
            operational_model=MODEL_10_ID,
        )
        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(order))
        signal = MT5DemoRobotSignal(
            symbol="XAUUSD",
            timeframe="M5",
            candle_time="2026-08-10T20:00:00+00:00",
            decision="BUY",
            confidence=1.0,
            active_model="M10_SETUP_C_XAU_M5",
            reason="filtros liberados",
            operational_model=MODEL_10_ID,
        )
        plan = MT5DemoTradePlan(
            symbol="XAUUSD",
            timeframe="M5",
            entry_price=120.0,
            stop=110.0,
            target=0.0,
            risk_reward=0.0,
            source="MODEL_10_MANUAL_RULE",
            operational_model=MODEL_10_ID,
        )
        self.assertEqual(MT5DemoRobotService()._trade_plan_validation(signal, plan), "")

    def test_position_manager_usa_beta_do_modelo_12_no_full_exit(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(59)] + [100.0]
        provider = _Provider(_candles(closes))
        base = Path(tempfile.gettempdir())
        manager = PositionManagerService(
            provider=provider,
            assisted_execution_enabled=True,
            log_path=base / "traderia-m12-position-test.jsonl",
            state_path=base / "traderia-m12-position-state.json",
            current_state_path=base / "traderia-m12-position-current.json",
        )
        spec = trend_filter_spec(MODEL_12_ID)
        result = manager.manage_plan(
            PositionTradePlan(
                symbol="XAUUSD",
                side="BUY",
                entry=110.0,
                stop=105.0,
                target=None,
                stop_management=spec.stop_management,  # type: ignore[union-attr]
                beta_id=spec.beta_id,  # type: ignore[union-attr]
                beta_version=spec.beta_version,  # type: ignore[union-attr]
                timeframe="M5",
                operational_model=MODEL_12_ID,
            )
        )
        self.assertEqual(result.status, "POSITION_CLOSED")
        self.assertEqual(result.beta_id, spec.beta_id)  # type: ignore[union-attr]
        self.assertEqual(provider.close_calls, 1)


class _Provider:
    def __init__(self, candles: list[dict[str, float | str]]) -> None:
        self.candles = candles
        self.close_calls = 0
        self.position = SimpleNamespace(
            ticket=12001,
            symbol="XAUUSD",
            side="BUY",
            type=0,
            price_open=110.0,
            sl=105.0,
            tp=0.0,
            volume=0.01,
        )

    def get_open_position(self, symbol: str) -> object | None:
        return self.position if symbol == "XAUUSD" else None

    def get_open_position_by_ticket(self, symbol: str, ticket: int) -> object | None:
        return self.position if ticket == 12001 else None

    def get_current_price(self, symbol: str) -> float:
        return 100.0

    def get_recent_candles(self, symbol: str, timeframe: str, limit: int) -> list[object]:
        return list(self.candles[-limit:])

    def get_atr(self, symbol: str, timeframe: str, period: int) -> None:
        return None

    def modify_position_sl(self, symbol: str, ticket: int, new_stop: float) -> object:
        return SimpleNamespace(success=True, message="SL atualizado")

    def close_position(self, **kwargs: object) -> object:
        self.close_calls += 1
        return SimpleNamespace(accepted=True, success=True, message="fechada")


if __name__ == "__main__":
    unittest.main()
