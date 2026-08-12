"""Tests for the independent M8-M14 dynamic-exit model family."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from application.dashboard_service import DashboardService, MT5_OPERATIONAL_MODEL_IDS
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.dynamic_exit_model_family import (
    DYNAMIC_EXIT_MODEL_IDS,
    DYNAMIC_EXIT_MODEL_SPECS,
    DYNAMIC_EXIT_POLICY,
    MODEL_8_ID,
    MODEL_9_ID,
)
from application.mt5_demo_robot_service import MT5DemoRobotService, MT5DemoRobotSignal
from application.position_manager_service import PositionManagerService, PositionTradePlan
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan


class DynamicExitModelFamilyTest(unittest.TestCase):
    """Protects model identity, entry parity and protect-only execution."""

    def test_family_m8_m14_is_preserved_but_retired(self) -> None:
        self.assertEqual(len(DYNAMIC_EXIT_MODEL_SPECS), 7)
        self.assertEqual(
            [(spec.number, spec.source_number) for spec in DYNAMIC_EXIT_MODEL_SPECS],
            list(zip(range(8, 15), range(1, 8))),
        )
        self.assertTrue(all(not is_active_operational_model(item) for item in DYNAMIC_EXIT_MODEL_IDS))
        self.assertTrue(all(is_retired_operational_model(item) for item in DYNAMIC_EXIT_MODEL_IDS))
        self.assertTrue(is_retired_operational_model("MODELO_8_TREND_PULLBACK_H1_M5"))

    def test_m8_preserves_m1_entry_sl_tp_and_changes_only_exit_contract(self) -> None:
        service = DashboardService()
        source_row = DashboardMT5ForexSignalRowViewModel(
            pair="EURUSD",
            active_model="TREND_MOMENTUM",
            active_model_indicators=("EMA20", "EMA50"),
            decision="BUY",
            theoretical_entry_direction="BUY",
            theoretical_entry_status="SINAL_TEORICO",
        )
        source_plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="H1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1150,
            risk_reward=3.0,
            stop_multiplier=2.0,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=0.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            stop_management="RESEARCH_FIXED_SL_TP",
            stop_management_parameters={"source_parameter": "preserved"},
            alpha_id="ALPHA013",
            beta_id="BETA003",
        )

        row, plan = service._mt5_dynamic_exit_variant_from_source(
            source_row,
            source_plan,
            operational_model=MODEL_8_ID,
        )

        self.assertEqual(plan.direction, source_plan.direction)
        self.assertEqual(plan.entry_price, source_plan.entry_price)
        self.assertEqual(plan.stop, source_plan.stop)
        self.assertEqual(plan.target, source_plan.target)
        self.assertEqual(plan.risk_reward, source_plan.risk_reward)
        self.assertEqual(plan.alpha_id, source_plan.alpha_id)
        self.assertEqual(plan.stop_management, DYNAMIC_EXIT_POLICY)
        self.assertEqual(plan.stop_management_parameters["source_parameter"], "preserved")
        self.assertFalse(plan.stop_management_parameters["early_exit_enabled"])
        self.assertFalse(plan.stop_management_parameters["full_exit_enabled"])
        self.assertEqual(row.research_plan_stop_management, DYNAMIC_EXIT_POLICY)
        self.assertIn("M8_DYNAMIC_FROM_M1", row.active_model)

    def test_all_models_calculates_twelve_active_entry_sources(self) -> None:
        class AllModelsService(DashboardService):
            def _mt5_operational_models_to_evaluate(self) -> tuple[str, ...]:
                return MT5_OPERATIONAL_MODEL_IDS

        service = AllModelsService()

        self.assertEqual(
            service._mt5_entry_source_models_to_evaluate(),
            MT5_OPERATIONAL_MODEL_IDS,
        )

    def test_dynamic_variants_preserve_entry_regime_contract_of_source(self) -> None:
        robot = MT5DemoRobotService()
        base = dict(
            symbol="EURUSD",
            timeframe="H1",
            candle_time="2026-08-05T18:00:00+00:00",
            decision="BUY",
            confidence=0.75,
            active_model="TREND_MOMENTUM",
            reason="Audit entry parity.",
        )

        m8_signal = MT5DemoRobotSignal(**base, operational_model=MODEL_8_ID)
        m9_signal = MT5DemoRobotSignal(**base, operational_model=MODEL_9_ID)

        self.assertIs(robot._regime_validation_signal(m8_signal), m8_signal)
        self.assertIsNone(robot._regime_validation_signal(m9_signal))

    def test_dynamic_protect_only_moves_sl_but_never_closes_position(self) -> None:
        provider = _PositionProvider()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manager = PositionManagerService(
                provider=provider,
                assisted_execution_enabled=True,
                early_exit_enabled=True,
                log_path=base / "history.jsonl",
                state_path=base / "state.json",
                current_state_path=base / "current.json",
            )
            result = manager.manage_plan(
                PositionTradePlan(
                    symbol="EURUSD",
                    side="BUY",
                    entry=1.1000,
                    stop=1.0980,
                    target=1.1060,
                    stop_management=DYNAMIC_EXIT_POLICY,
                    stop_management_parameters={
                        "break_even_trigger_rr": 1.5,
                        "atr_trailing_activation_rr": 1.5,
                        "atr_trailing_factor": 2.0,
                    },
                    atr=0.0010,
                    momentum=-0.0010,
                    risk_reward=3.0,
                    operational_model=MODEL_8_ID,
                    beta_id="BETA008_DYNAMIC_FROM_M1",
                    beta_mode="DYNAMIC_PROTECT_ONLY",
                )
            )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertGreater(provider.modified_stop or 0.0, 1.0980)
        self.assertEqual(provider.close_calls, 0)
        self.assertNotIn(result.action, {"EARLY_EXIT", "FULL_EXIT"})


class _PositionProvider:
    def __init__(self) -> None:
        self.position = SimpleNamespace(
            ticket=808,
            symbol="EURUSD",
            side="BUY",
            type=0,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1060,
            volume=0.1,
        )
        self.modified_stop: float | None = None
        self.close_calls = 0

    def get_open_position(self, symbol: str) -> object | None:
        return self.position if symbol.upper() == "EURUSD" else None

    def get_open_position_by_ticket(self, symbol: str, ticket: int) -> object | None:
        if symbol.upper() == "EURUSD" and ticket == 808:
            return self.position
        return None

    def get_current_price(self, symbol: str) -> float | None:
        return 1.1032 if symbol.upper() == "EURUSD" else None

    def get_recent_candles(self, symbol: str, timeframe: str, limit: int) -> list[object]:
        return []

    def get_atr(self, symbol: str, timeframe: str, period: int) -> float | None:
        return 0.0010

    def modify_position_sl(self, symbol: str, ticket: int, new_stop: float) -> object:
        self.modified_stop = new_stop
        return SimpleNamespace(success=True, message="SL atualizado.")

    def close_position(self, **kwargs: object) -> object:
        self.close_calls += 1
        return SimpleNamespace(accepted=True, status="ACCEPTED", message="Fechada.")


if __name__ == "__main__":
    unittest.main()
