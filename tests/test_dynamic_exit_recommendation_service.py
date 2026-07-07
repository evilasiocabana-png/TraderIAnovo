import unittest

from application.dynamic_exit_recommendation_service import (
    DynamicExitRecommendationEngine,
)
from domain.contracts.dynamic_exit import DynamicExitMarketReading


class DynamicExitRecommendationEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DynamicExitRecommendationEngine()

    def test_invalid_plan_returns_bad_context_without_execution(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="NEW_POSITION"),
            policy="ATR_TRAILING_STOP",
            plan_status="SEM_PLANO",
        )

        self.assertEqual(recommendation.action, "NO_ACTION_BAD_CONTEXT")
        self.assertFalse(recommendation.allowed_to_execute_demo)
        self.assertIn("Read-only:", recommendation.reason)

    def test_new_position_keeps_original_plan(self) -> None:
        recommendation = self.engine.recommend(self._reading(state="NEW_POSITION"))

        self.assertEqual(recommendation.action, "KEEP_ORIGINAL_PLAN")
        self.assertGreater(recommendation.confidence, 0.0)

    def test_trend_runner_with_atr_uses_atr_trailing(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="TREND_RUNNER", r_multiple=1.4),
            policy="ATR_TRAILING_STOP",
        )

        self.assertEqual(recommendation.action, "TRAIL_BY_ATR")
        self.assertEqual(recommendation.market_state, "TREND_RUNNER")

    def test_trend_runner_with_structure_policy_uses_structure_trailing(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="TREND_RUNNER", r_multiple=1.2),
            policy="DONCHIAN_CHANNEL_STOP",
        )

        self.assertEqual(recommendation.action, "TRAIL_BY_STRUCTURE")

    def test_reversal_risk_with_break_even_recommends_protection(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="REVERSAL_RISK", r_multiple=0.5),
            policy="BREAK_EVEN",
        )

        self.assertEqual(recommendation.action, "PROTECT_TO_BREAK_EVEN")
        self.assertEqual(recommendation.candidate_stop, 1.1000)
        self.assertFalse(recommendation.allowed_to_execute_demo)

    def test_reversal_risk_without_break_even_tightens_by_momentum_loss(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="REVERSAL_RISK", r_multiple=0.5),
            policy="ATR_TRAILING_STOP",
        )

        self.assertEqual(recommendation.action, "TIGHTEN_BY_MOMENTUM_LOSS")

    def test_time_decay_returns_watch_action(self) -> None:
        recommendation = self.engine.recommend(self._reading(state="TIME_DECAY"))

        self.assertEqual(recommendation.action, "TIME_DECAY_EXIT_WATCH")

    def test_bad_context_never_executes(self) -> None:
        recommendation = self.engine.recommend(
            self._reading(state="BAD_EXECUTION_CONTEXT")
        )

        self.assertEqual(recommendation.action, "NO_ACTION_BAD_CONTEXT")
        self.assertEqual(recommendation.confidence, 0.0)
        self.assertFalse(recommendation.allowed_to_execute_demo)

    def _reading(
        self,
        *,
        state: str,
        r_multiple: float = 0.0,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side="BUY",
            is_positioned=state != "NO_POSITION",
            current_price=1.1010,
            entry_price=1.1000,
            stop_price=1.0990,
            target_price=1.1040,
            state=state,
            r_multiple=r_multiple,
            reason=f"Estado {state} em teste.",
            candidate_stop=1.0990,
        )


if __name__ == "__main__":
    unittest.main()
