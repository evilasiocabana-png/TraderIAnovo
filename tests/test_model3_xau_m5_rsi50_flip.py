import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

from application.model3_all_forex_winners import MODEL_3_ID as HISTORICAL_MODEL_3_ID
from application.model3_xau_m5_rsi50_flip import (
    MODEL_3_ID,
    MODEL_3_SYMBOL,
    MODEL_3_TIMEFRAME,
    evaluate_model3_entry,
    evaluate_model3_exit,
    model3_parameters,
)
from application.position_manager_service import (
    PositionManagerService,
    PositionTradePlan,
)
from application.demo_execution_service import DemoExecutionService
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


def candles(closes: list[float]) -> list[dict[str, object]]:
    closes = [closes[0]] * max(201 - len(closes), 0) + list(closes)
    return [
        {
            "time": f"2026-08-{index // 288 + 1:02d} {(index % 288) // 12:02d}:{(index % 12) * 5:02d}",
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
        }
        for index, close in enumerate(closes)
    ]


class Model3XauM5Rsi50FlipTests(unittest.TestCase):
    def test_identity_scope_and_retirement_are_isolated(self) -> None:
        self.assertEqual(MODEL_3_SYMBOL, "XAUUSD")
        self.assertEqual(MODEL_3_TIMEFRAME, "M5")
        self.assertFalse(is_active_operational_model(MODEL_3_ID))
        self.assertTrue(is_retired_operational_model(MODEL_3_ID))
        self.assertFalse(is_active_operational_model(HISTORICAL_MODEL_3_ID))
        self.assertTrue(is_retired_operational_model(HISTORICAL_MODEL_3_ID))

    def test_rsi_above_50_prepares_buy_with_structural_stop(self) -> None:
        rows = candles(
            [90 + index * 0.1 for index in range(31)]
            + [100, 101, 102, 99, 101, 103, 100, 102, 104, 101, 103, 105,
               102, 104, 106, 103, 105, 107, 109, 111, 112]
        )
        decision = evaluate_model3_entry(rows)
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")
        self.assertGreater(decision.rsi14 or 0.0, 50.0)
        self.assertGreater(decision.closed_price or 0.0, decision.sma20 or 0.0)
        self.assertLess(decision.initial_stop or 0.0, decision.entry_price or 0.0)

    def test_rsi_below_50_prepares_sell_with_structural_stop(self) -> None:
        rows = candles(
            [122 - index * 0.1 for index in range(31)]
            + [112, 111, 110, 113, 111, 109, 112, 110, 108, 111, 109, 107,
               110, 108, 106, 109, 107, 105, 103, 101, 100]
        )
        decision = evaluate_model3_entry(rows)
        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "SELL")
        self.assertLess(decision.rsi14 or 100.0, 50.0)
        self.assertLess(decision.closed_price or 999.0, decision.sma20 or 0.0)
        self.assertGreater(decision.initial_stop or 0.0, decision.entry_price or 0.0)

    def test_position_is_closed_only_when_rsi_moves_to_opposite_side(self) -> None:
        rising = candles(list(range(100, 117)))
        falling = candles(list(range(117, 100, -1)))
        self.assertEqual(evaluate_model3_exit(rising, "BUY").action, "HOLD_POSITION")
        self.assertEqual(evaluate_model3_exit(rising, "SELL").action, "FULL_EXIT")
        self.assertEqual(evaluate_model3_exit(falling, "SELL").action, "HOLD_POSITION")
        self.assertEqual(evaluate_model3_exit(falling, "BUY").action, "FULL_EXIT")

    def test_parameters_freeze_reverse_contract(self) -> None:
        parameters = model3_parameters()
        self.assertEqual(parameters["buy_rule"], "CLOSED_RSI14>50_AND_CLOSE>SMA20")
        self.assertEqual(parameters["sell_rule"], "CLOSED_RSI14<50_AND_CLOSE<SMA20")
        self.assertEqual(parameters["sma_period"], 20)
        self.assertEqual(parameters["lookback_candles"], 200)
        self.assertTrue(parameters["reverse_after_full_exit"])
        self.assertFalse(parameters["take_profit_enabled"])

    def test_position_manager_full_exit_buy_when_closed_rsi_is_below_50(self) -> None:
        provider = _PositionProvider(candles(list(range(117, 99, -1))))
        base = Path(tempfile.gettempdir())
        manager = PositionManagerService(
            provider=provider,
            assisted_execution_enabled=True,
            log_path=base / "traderia-m3-position-test.jsonl",
            state_path=base / "traderia-m3-position-state.json",
            current_state_path=base / "traderia-m3-position-current.json",
        )
        result = manager.manage_plan(
            PositionTradePlan(
                symbol="XAUUSD",
                side="BUY",
                entry=110.0,
                stop=105.0,
                target=None,
                stop_management="M3_RSI50_POSITION_FLIP",
                beta_id="BETAXAU3_RSI50_POSITION_FLIP",
                beta_version="M3_EXIT_V1",
                beta_mode="FULL_EXIT_AND_REVERSE_RSI50",
                timeframe="M5",
                operational_model=MODEL_3_ID,
            )
        )
        self.assertEqual(result.status, "POSITION_CLOSED")
        self.assertEqual(provider.close_calls, 1)

    def test_executor_and_robot_accept_m3_without_fixed_target(self) -> None:
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=3500.0,
            stop=3490.0,
            target=0.0,
            operational_model=MODEL_3_ID,
        )
        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(order))
        signal = MT5DemoRobotSignal(
            symbol="XAUUSD",
            timeframe="M5",
            candle_time="2026-08-11T10:00:00+00:00",
            decision="BUY",
            confidence=1.0,
            active_model="M3_XAU_M5_RSI14_FLIP",
            reason="RSI14 acima de 50.",
            operational_model=MODEL_3_ID,
        )
        plan = MT5DemoTradePlan(
            symbol="XAUUSD",
            timeframe="M5",
            entry_price=3500.0,
            stop=3490.0,
            target=0.0,
            risk_reward=0.0,
            source="MODEL_3_MANUAL_RULE",
            operational_model=MODEL_3_ID,
        )
        self.assertEqual(MT5DemoRobotService()._trade_plan_validation(signal, plan), "")


class _PositionProvider:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.close_calls = 0
        self.position = SimpleNamespace(
            ticket=3001,
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
        return self.position if symbol == "XAUUSD" and ticket == 3001 else None

    def get_current_price(self, symbol: str) -> float:
        return 100.0

    def get_recent_candles(self, symbol: str, timeframe: str, limit: int) -> list[object]:
        return list(self.rows[-limit:])

    def get_atr(self, symbol: str, timeframe: str, period: int) -> None:
        return None

    def modify_position_sl(self, symbol: str, ticket: int, new_stop: float) -> object:
        return SimpleNamespace(success=True, message="SL atualizado")

    def close_position(self, **kwargs: object) -> object:
        self.close_calls += 1
        return SimpleNamespace(accepted=True, success=True, message="fechada")


if __name__ == "__main__":
    unittest.main()
