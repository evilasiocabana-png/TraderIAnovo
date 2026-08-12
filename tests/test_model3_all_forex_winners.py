import unittest

from application.model3_all_forex_winners import MODEL_3_ID, MODEL_3_SCOPE
from domain.market_universe import (
    MODEL_1_FOREX_PAIRS,
    MODEL_6_FOREX_EXPANSION_PAIRS,
    MODEL_7_ALTERNATIVE_MARKETS,
)
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)


class Model3AllForexWinnersTests(unittest.TestCase):
    def test_scope_contains_all_17_currency_pairs_only(self) -> None:
        self.assertEqual(
            MODEL_3_SCOPE,
            (*MODEL_1_FOREX_PAIRS, *MODEL_6_FOREX_EXPANSION_PAIRS),
        )
        self.assertEqual(len(MODEL_3_SCOPE), 17)
        self.assertEqual(len(set(MODEL_3_SCOPE)), 17)
        self.assertTrue(set(MODEL_3_SCOPE).isdisjoint(MODEL_7_ALTERNATIVE_MARKETS))

    def test_previous_m3_contract_is_historical_and_retired(self) -> None:
        self.assertFalse(is_active_operational_model(MODEL_3_ID))
        self.assertTrue(is_retired_operational_model(MODEL_3_ID))
        self.assertTrue(
            is_retired_operational_model("MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS")
        )
        self.assertTrue(is_retired_operational_model("MODELO_3_RR3"))


if __name__ == "__main__":
    unittest.main()
