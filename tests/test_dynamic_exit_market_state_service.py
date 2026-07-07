import unittest

from application.dynamic_exit_market_state_service import (
    DynamicExitMarketStateClassifier,
    is_dynamic_exit_market_state,
)
from domain.contracts.dynamic_exit import DynamicExitMarketReading


class DynamicExitMarketStateClassifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = DynamicExitMarketStateClassifier()

    def test_no_position(self) -> None:
        reading = self.classifier.classify(DynamicExitMarketReading())

        self.assertEqual(reading.state, "NO_POSITION")
        self.assertEqual(reading.r_multiple, 0.0)

    def test_bad_execution_context_when_stop_is_missing(self) -> None:
        reading = self.classifier.classify(
            DynamicExitMarketReading(
                symbol="EURUSD",
                side="BUY",
                is_positioned=True,
                current_price=1.1010,
                entry_price=1.1000,
            )
        )

        self.assertEqual(reading.state, "BAD_EXECUTION_CONTEXT")
        self.assertIn("Stop atual ausente", reading.reason)

    def test_new_position_before_confirmation(self) -> None:
        reading = self.classifier.classify(
            self._reading(current_price=1.1002, momentum=0.1)
        )

        self.assertEqual(reading.state, "NEW_POSITION")
        self.assertLess(reading.r_multiple, 1.0)

    def test_protected_position_when_stop_protects_entry(self) -> None:
        reading = self.classifier.classify(
            self._reading(current_price=1.10005, stop_price=1.1001)
        )

        self.assertEqual(reading.state, "PROTECTED_POSITION")

    def test_trend_runner_after_one_r_with_favorable_momentum(self) -> None:
        reading = self.classifier.classify(
            self._reading(current_price=1.1025, momentum=0.4)
        )

        self.assertEqual(reading.state, "TREND_RUNNER")
        self.assertGreaterEqual(reading.r_multiple, 1.0)

    def test_reversal_risk_when_momentum_turns_against_position(self) -> None:
        reading = self.classifier.classify(
            self._reading(current_price=1.1010, momentum=-0.5)
        )

        self.assertEqual(reading.state, "REVERSAL_RISK")

    def test_time_decay_when_trade_stalls_for_long_period(self) -> None:
        reading = self.classifier.classify(
            self._reading(
                current_price=1.1001,
                momentum=0.0,
                time_in_position_minutes=260,
            )
        )

        self.assertEqual(reading.state, "TIME_DECAY")

    def test_all_reported_states_belong_to_contract(self) -> None:
        states = {
            "NO_POSITION",
            "NEW_POSITION",
            "PROTECTED_POSITION",
            "TREND_RUNNER",
            "REVERSAL_RISK",
            "TIME_DECAY",
            "BAD_EXECUTION_CONTEXT",
        }

        self.assertTrue(all(is_dynamic_exit_market_state(state) for state in states))

    def _reading(
        self,
        *,
        current_price: float,
        stop_price: float = 1.0990,
        momentum: float | None = None,
        time_in_position_minutes: float | None = None,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side="BUY",
            is_positioned=True,
            current_price=current_price,
            entry_price=1.1000,
            stop_price=stop_price,
            target_price=1.1040,
            momentum=momentum,
            spread=0.00001,
            time_in_position_minutes=time_in_position_minutes,
        )


if __name__ == "__main__":
    unittest.main()
