from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from application.model8_xau_m5_sma_rsi_reentry import (
    MODEL_8_ID,
    evaluate_model8_entry,
    evaluate_model8_exit,
    load_model8_runtime_state,
    model8_parameters,
    update_model8_runtime_state,
)
from application.demo_execution_service import DemoExecutionService
from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.position_manager_service import PositionManagerService, PositionTradePlan
from application.mt5_demo_robot_service import (
    MT5DemoRobotService,
    MT5DemoRobotSignal,
    MT5DemoTradePlan,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _candles(closes: list[float], *, pivot: str = "low") -> list[dict[str, float | str]]:
    closes = [closes[0]] * max(200 - len(closes), 0) + list(closes)
    rows: list[dict[str, float | str]] = []
    for index, close in enumerate(closes):
        low = close - 0.5
        high = close + 0.5
        if index == len(closes) - 6:
            if pivot == "low":
                low = close - 2.0
            else:
                high = close + 2.0
        rows.append(
            {
                "time": f"2026-08-{index // 288 + 1:02d}T{(index % 288) // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
                "open": close,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    current = closes[-1]
    rows.append(
        {
            "time": "2026-08-02T00:00:00+00:00",
            "open": current,
            "high": current + 0.4,
            "low": current - 0.4,
            "close": current,
        }
    )
    return rows


class Model8XauM5Test(unittest.TestCase):
    def test_identidade_e_parametros_congelados(self) -> None:
        self.assertEqual(MODEL_8_ID, "MODELO_8_XAU_M5_SMA_RSI_REENTRY")
        params = model8_parameters()
        self.assertEqual(params["symbol"], "XAUUSD")
        self.assertEqual(params["timeframe"], "M5")
        self.assertEqual(params["sma_fast"], 20)
        self.assertEqual(params["sma_slow"], 50)
        self.assertEqual(params["rsi_period"], 14)
        self.assertEqual(
            params["entry_order_type"],
            "MARKET_ON_CONFIRMED_CLOSED_M5_SMA20_50_CROSS_WITH_RSI50",
        )
        self.assertTrue(params["initial_entry_requires_fresh_sma_cross"])
        self.assertFalse(params["take_profit_enabled"])
        self.assertTrue(params["full_exit_enabled"])
        self.assertTrue(is_active_operational_model(MODEL_8_ID))
        self.assertFalse(is_retired_operational_model(MODEL_8_ID))
        self.assertTrue(
            is_retired_operational_model("MODELO_8_DYNAMIC_EXIT_FROM_M1")
        )

    def test_compra_quando_rsi_acima_de_50_e_sma20_acima_da_sma50(self) -> None:
        closes = ([100.0] * 30) + ([99.0] * 20) + [120.0]
        decision = evaluate_model8_entry(_candles(closes, pivot="low"))
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")
        self.assertEqual(decision.signal_kind, "SMA20_50_CROSS")
        self.assertGreater(decision.rsi14 or 0.0, 50.0)
        self.assertLess(decision.initial_stop or 0.0, decision.entry_price or 0.0)

    def test_tendencia_buy_ja_cruzada_nao_vira_primeira_entrada(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        decision = evaluate_model8_entry(_candles(closes, pivot="low"))
        self.assertFalse(decision.ready)
        self.assertEqual(decision.direction, "WAIT")
        self.assertEqual(decision.signal_kind, "REENTRY")
        self.assertEqual(
            decision.status,
            "M8_REENTRY_AGUARDA_RECUO_ESTRUTURAL_M5",
        )
        self.assertGreater(decision.rsi14 or 0.0, 50.0)
        self.assertGreater(decision.sma20 or 0.0, decision.sma50 or 0.0)

    def test_venda_quando_rsi_abaixo_de_50_e_sma20_abaixo_da_sma50(self) -> None:
        closes = ([100.0] * 30) + ([101.0] * 20) + [80.0]
        decision = evaluate_model8_entry(_candles(closes, pivot="high"))
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "SELL")
        self.assertEqual(decision.signal_kind, "SMA20_50_CROSS")
        self.assertLess(decision.rsi14 or 100.0, 50.0)
        self.assertGreater(decision.initial_stop or 0.0, decision.entry_price or 0.0)

    def test_reentrada_buy_pelo_rsi_enquanto_tendencia_permanece(self) -> None:
        closes = ([100.0 + (index * 0.2) for index in range(58)]) + [112.0, 111.0]
        candles = _candles(closes, pivot="low")
        candles[-4]["high"] = 120.0
        decision = evaluate_model8_entry(
            candles,
            awaiting_reentry_side="BUY",
        )
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")
        self.assertEqual(decision.signal_kind, "REENTRY")
        self.assertEqual(decision.entry_order_type, "BUY_STOP")
        self.assertAlmostEqual(decision.entry_price or 0.0, closes[-1] + 0.5)
        self.assertEqual(decision.structural_target_price, 120.0)

    def test_reentrada_sell_stop_apos_recuo_ascendente(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(58)] + [108.0, 109.0]
        candles = _candles(closes, pivot="high")
        candles[-4]["low"] = 100.0
        decision = evaluate_model8_entry(
            candles,
            awaiting_reentry_side="SELL",
        )
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "SELL")
        self.assertEqual(decision.signal_kind, "REENTRY")
        self.assertEqual(decision.entry_order_type, "SELL_STOP")
        self.assertAlmostEqual(decision.entry_price or 0.0, closes[-1] - 0.5)
        self.assertEqual(decision.structural_target_price, 100.0)

    def test_sell_ja_cruzado_sem_estado_usa_reentrada_stop_apos_recuo(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(58)] + [108.0, 109.0]
        candles = _candles(closes, pivot="high")
        candles[-4]["low"] = 100.0

        decision = evaluate_model8_entry(candles)

        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "SELL")
        self.assertEqual(decision.signal_kind, "REENTRY")
        self.assertEqual(decision.entry_order_type, "SELL_STOP")

    def test_reentrada_sell_aguarda_recuo_ascendente(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(60)]
        decision = evaluate_model8_entry(
            _candles(closes, pivot="high"),
            awaiting_reentry_side="SELL",
        )
        self.assertFalse(decision.ready)
        self.assertEqual(decision.direction, "WAIT")
        self.assertEqual(
            decision.status,
            "M8_REENTRY_AGUARDA_RECUO_ESTRUTURAL_M5",
        )

    def test_reentrada_buy_aguarda_recuo_descendente(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        decision = evaluate_model8_entry(
            _candles(closes, pivot="low"),
            awaiting_reentry_side="BUY",
        )
        self.assertFalse(decision.ready)
        self.assertEqual(decision.direction, "WAIT")
        self.assertEqual(
            decision.status,
            "M8_REENTRY_AGUARDA_RECUO_ESTRUTURAL_M5",
        )

    def test_compra_permanece_aberta_enquanto_rsi_esta_acima_de_50(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        decision = evaluate_model8_exit(_candles(closes), "BUY")
        self.assertEqual(decision.action, "HOLD_POSITION")
        self.assertTrue(decision.extreme_armed)
        self.assertGreaterEqual(decision.rsi14 or 0.0, 50.0)

    def test_compra_fecha_no_cruzamento_confirmado_de_70_para_baixo(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(59)] + [100.0]
        decision = evaluate_model8_exit(_candles(closes), "BUY")
        self.assertEqual(decision.action, "FULL_EXIT")
        self.assertGreaterEqual(decision.previous_rsi14 or 0.0, 70.0)
        self.assertLess(decision.rsi14 or 100.0, 70.0)
        self.assertEqual(decision.status, "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY")

    def test_venda_fecha_no_cruzamento_confirmado_de_30_para_cima(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(59)] + [120.0]
        decision = evaluate_model8_exit(_candles(closes), "SELL")
        self.assertEqual(decision.action, "FULL_EXIT")
        self.assertIsNotNone(decision.previous_rsi14)
        self.assertLessEqual(float(decision.previous_rsi14), 30.0)
        self.assertGreater(decision.rsi14 or 0.0, 30.0)
        self.assertEqual(decision.status, "M8_EXIT_RSI30_CRUZOU_PARA_CIMA_SELL")

    def test_compra_nao_fecha_abaixo_de_50_sem_novo_cruzamento_de_70(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(58)] + [100.0, 100.0]
        decision = evaluate_model8_exit(_candles(closes), "BUY")
        self.assertLess(decision.previous_rsi14 or 100.0, 70.0)
        self.assertLess(decision.rsi14 or 100.0, 50.0)
        self.assertEqual(decision.action, "HOLD_POSITION")

    def test_reentrada_buy_fecha_se_rsi_cruza_50_para_baixo(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(45.0, 60.0),
        ):
            decision = evaluate_model8_exit(
                _candles(closes),
                "BUY",
                reentry_position=True,
            )
        self.assertEqual(decision.action, "FULL_EXIT")
        self.assertEqual(
            decision.status,
            "M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_BAIXO_BUY",
        )

    def test_reentrada_sell_fecha_se_rsi_cruza_50_para_cima(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(60)]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(55.0, 40.0),
        ):
            decision = evaluate_model8_exit(
                _candles(closes),
                "SELL",
                reentry_position=True,
            )
        self.assertEqual(decision.action, "FULL_EXIT")
        self.assertEqual(
            decision.status,
            "M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_CIMA_SELL",
        )

    def test_reentrada_buy_fecha_mesmo_se_app_reiniciou_apos_perder_rsi50(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(45.0, 45.0),
        ):
            decision = evaluate_model8_exit(
                _candles(closes),
                "BUY",
                reentry_position=True,
            )
        self.assertEqual(decision.action, "FULL_EXIT")

    def test_reentrada_sell_fecha_mesmo_se_app_reiniciou_apos_perder_rsi50(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(60)]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(55.0, 55.0),
        ):
            decision = evaluate_model8_exit(
                _candles(closes),
                "SELL",
                reentry_position=True,
            )
        self.assertEqual(decision.action, "FULL_EXIT")

    def test_entrada_inicial_nao_usa_saida_adicional_do_rsi50(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(60)]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(45.0, 60.0),
        ):
            decision = evaluate_model8_exit(
                _candles(closes),
                "BUY",
                reentry_position=False,
            )
        self.assertEqual(decision.action, "HOLD_POSITION")

    def test_posicao_fecha_quando_medias_invertem(self) -> None:
        buy_closes = ([100.0] * 30) + ([101.0] * 20) + [80.0]
        buy = evaluate_model8_exit(_candles(buy_closes), "BUY")
        self.assertEqual(buy.action, "FULL_EXIT")
        self.assertEqual(buy.status, "M8_EXIT_INVERSAO_SMA_BUY")

    def test_m24_principal_ignora_inversao_sma_e_preserva_saida_rsi(self) -> None:
        buy_closes = ([100.0] * 30) + ([101.0] * 20) + [80.0]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(60.0, 60.0),
        ):
            hold = evaluate_model8_exit(
                _candles(buy_closes),
                "BUY",
                sma_inversion_exit_enabled=False,
            )
        self.assertEqual(hold.action, "HOLD_POSITION")
        self.assertEqual(hold.status, "M8_HOLD_BUY")

        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(69.0, 71.0),
        ):
            rsi_exit = evaluate_model8_exit(
                _candles(buy_closes),
                "BUY",
                sma_inversion_exit_enabled=False,
            )
        self.assertEqual(rsi_exit.action, "FULL_EXIT")
        self.assertEqual(
            rsi_exit.status,
            "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
        )

        sell_closes = ([100.0] * 30) + ([99.0] * 20) + [120.0]
        with patch(
            "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
            side_effect=(40.0, 40.0),
        ):
            sell_hold = evaluate_model8_exit(
                _candles(sell_closes),
                "SELL",
                sma_inversion_exit_enabled=False,
            )
        self.assertEqual(sell_hold.action, "HOLD_POSITION")
        self.assertEqual(sell_hold.status, "M8_HOLD_SELL")

    def test_estado_de_reentrada_e_atomico_e_isolado(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model8.json"
            update_model8_runtime_state(
                entry_intent_side="BUY",
                entry_intent_kind="REENTRY",
                last_exit_status="M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
                path=path,
            )
            state = load_model8_runtime_state(path)
            self.assertEqual(state["entry_intent_side"], "BUY")
            self.assertEqual(state["entry_intent_kind"], "REENTRY")
            self.assertEqual(
                state["last_exit_status"],
                "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
            )

    def test_ordem_m8_nao_exige_tp_fixo(self) -> None:
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=111.0,
            stop=108.0,
            target=0.0,
            operational_model=MODEL_8_ID,
        )
        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(order))

    def test_robo_autoriza_fonte_m8_e_plano_sem_tp(self) -> None:
        signal = MT5DemoRobotSignal(
            symbol="XAUUSD",
            timeframe="M5",
            candle_time="2026-08-10T20:00:00+00:00",
            decision="BUY",
            confidence=1.0,
            active_model="M8_XAU_M5_SMA20_50_RSI14",
            reason="RSI14 acima de 50 com SMA20 acima da SMA50.",
            operational_model=MODEL_8_ID,
        )
        plan = MT5DemoTradePlan(
            symbol="XAUUSD",
            timeframe="M5",
            entry_price=120.0,
            stop=98.99,
            target=0.0,
            risk_reward=0.0,
            source="MODEL_8_MANUAL_RULE",
            operational_model=MODEL_8_ID,
        )
        self.assertEqual(MT5DemoRobotService()._trade_plan_validation(signal, plan), "")

    def test_dashboard_materializa_plano_m8_a_mercado_sem_tp(self) -> None:
        closes = ([100.0] * 30) + ([99.0] * 20) + [120.0]
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(
                latest_forex_candles={
                    ("XAUUSD", "M5"): _candles(closes, pivot="low")
                }
            ),
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
            return_value={},
        ):
            row, plan = service._mt5_model8_xau_m5_plan(
                DashboardMT5ForexSignalRowViewModel(pair="XAUUSD"),
                fallback,
            )
        self.assertEqual(row.decision, "BUY")
        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.source, "MODEL_8_MANUAL_RULE")
        self.assertEqual(plan.target, 0.0)
        self.assertEqual(plan.entry_price, closes[-1])

    def test_dashboard_materializa_reentrada_m8_com_buy_stop(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(58)] + [112.0, 111.0]
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(
                latest_forex_candles={
                    ("XAUUSD", "M5"): _candles(closes, pivot="low")
                }
            ),
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
            row, plan = service._mt5_model8_xau_m5_plan(
                DashboardMT5ForexSignalRowViewModel(pair="XAUUSD"),
                fallback,
            )
        self.assertEqual(row.theoretical_entry_status, "ORDEM_STOP_TEORICA")
        self.assertAlmostEqual(plan.entry_price or 0.0, closes[-1] + 0.5)
        self.assertEqual(
            plan.stop_management_parameters["active_entry_order_type"],
            "BUY_STOP",
        )

    def test_position_manager_executa_full_exit_buy_no_cruzamento_de_70(self) -> None:
        closes = [100.0 + (index * 0.2) for index in range(59)] + [100.0]
        provider = _PositionProvider(_candles(closes))
        base = Path(tempfile.gettempdir())
        manager = PositionManagerService(
            provider=provider,
            assisted_execution_enabled=True,
            log_path=base / "traderia-m8-position-test.jsonl",
            state_path=base / "traderia-m8-position-state.json",
            current_state_path=base / "traderia-m8-position-current.json",
        )
        plan = PositionTradePlan(
            symbol="XAUUSD",
            side="BUY",
            entry=110.0,
            stop=105.0,
            target=None,
            stop_management="M8_SMA_RSI_FULL_EXIT",
            beta_id="BETAXAU8_RSI70_30_SMA_FULL_EXIT",
            beta_version="M8_EXIT_V3",
            beta_mode="FULL_EXIT_RSI70_30_CROSS_OR_SMA_INVERSION",
            timeframe="M5",
            operational_model=MODEL_8_ID,
        )
        with (
            patch("application.position_manager_service.load_model8_runtime_state", return_value={}),
            patch("application.position_manager_service.update_model8_runtime_state") as state_update,
        ):
            result = manager.manage_plan(plan)
        self.assertEqual(result.status, "POSITION_CLOSED")
        self.assertEqual(provider.close_calls, 1)
        state_update.assert_called_once()

    def test_position_manager_rearma_reentrada_xau_apos_saida_rsi50(self) -> None:
        closes = [120.0 - (index * 0.2) for index in range(60)]
        provider = _PositionProvider(_candles(closes))
        provider.position.side = "SELL"
        provider.position.type = 1
        provider.position.price_open = 110.0
        provider.position.sl = 115.0
        base = Path(tempfile.gettempdir())
        manager = PositionManagerService(
            provider=provider,
            assisted_execution_enabled=True,
            log_path=base / "traderia-m8-reentry-position-test.jsonl",
            state_path=base / "traderia-m8-reentry-position-state.json",
            current_state_path=base / "traderia-m8-reentry-position-current.json",
        )
        plan = PositionTradePlan(
            symbol="XAUUSD",
            side="SELL",
            entry=110.0,
            stop=115.0,
            target=100.0,
            stop_management="M8_SMA_RSI_FULL_EXIT",
            stop_management_parameters={"active_entry_order_type": "SELL_STOP"},
            beta_id="BETAXAU8_RSI70_30_SMA_FULL_EXIT",
            beta_version="M8_EXIT_V3",
            beta_mode="FULL_EXIT_RSI70_30_CROSS_OR_SMA_INVERSION",
            timeframe="M5",
            operational_model=MODEL_8_ID,
        )
        with (
            patch(
                "application.model8_xau_m5_sma_rsi_reentry._wilder_rsi",
                side_effect=(55.0, 40.0),
            ),
            patch(
                "application.position_manager_service.load_model8_runtime_state",
                return_value={},
            ),
            patch(
                "application.position_manager_service.update_model8_runtime_state"
            ) as state_update,
        ):
            result = manager.manage_plan(plan)

        self.assertEqual(result.status, "POSITION_CLOSED")
        self.assertEqual(provider.close_calls, 1)
        self.assertEqual(
            state_update.call_args.kwargs["entry_intent_side"],
            "SELL",
        )


class _PositionProvider:
    def __init__(self, candles: list[dict[str, float | str]]) -> None:
        self.candles = candles
        self.close_calls = 0
        self.position = SimpleNamespace(
            ticket=8001,
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
        return self.position if symbol == "XAUUSD" and ticket == 8001 else None

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
