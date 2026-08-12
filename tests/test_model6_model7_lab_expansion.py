import unittest

from application.model6_lab_forex_expansion import MODEL_6_ID, MODEL_6_SCOPE
from application.model7_lab_alternative_markets import MODEL_7_ID, MODEL_7_SCOPE
from application.position_manager_service import PositionManagerService, PositionTradePlan
from domain.market_universe import MT5_RESEARCH_MARKETS
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)


class Model6Model7LabExpansionTests(unittest.TestCase):
    def test_model_scopes_are_isolated(self) -> None:
        self.assertEqual(len(MODEL_6_SCOPE), 9)
        self.assertEqual(MODEL_7_SCOPE, ("XAUUSD", "BTCUSD"))
        self.assertTrue(set(MODEL_6_SCOPE).isdisjoint(MODEL_7_SCOPE))
        self.assertEqual(len(MT5_RESEARCH_MARKETS), 19)

    def test_new_ids_are_active_and_legacy_ids_are_retired(self) -> None:
        self.assertTrue(is_active_operational_model(MODEL_6_ID))
        self.assertTrue(is_active_operational_model(MODEL_7_ID))
        self.assertFalse(is_retired_operational_model(MODEL_6_ID))
        self.assertFalse(is_retired_operational_model(MODEL_7_ID))
        self.assertTrue(
            is_retired_operational_model("MODELO_6_TREND_MOMENTUM_ORIGINAL")
        )
        self.assertTrue(
            is_retired_operational_model("MODELO_7_TREND_MOMENTUM_DYNAMIC")
        )

    def test_new_lab_plans_do_not_inherit_historical_dynamic_exit(self) -> None:
        manager = object.__new__(PositionManagerService)
        plan = PositionTradePlan(
            symbol="XAUUSD",
            side="BUY",
            entry=2300.0,
            stop=2285.0,
            target=2337.5,
            stop_management="RESEARCH_FIXED_SL_TP",
            beta_id="BETA001",
            beta_mode="FIXED_SL_TP",
            operational_model=MODEL_7_ID,
            entry_setup="TREND_MOMENTUM",
        )
        self.assertFalse(manager._is_m6_original_plan(plan))
        self.assertFalse(manager._is_m7_dynamic_plan(plan))


if __name__ == "__main__":
    unittest.main()
