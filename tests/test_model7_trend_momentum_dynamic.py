"""Regression tests for the independent M7 dynamic-protection model."""

import unittest

from application.model7_trend_momentum_dynamic import (
    MODEL_7_ALPHA_ID,
    MODEL_7_ATR_STOP_FACTOR,
    MODEL_7_BETA_ID,
    MODEL_7_BETA_VERSION,
    MODEL_7_CANDLES,
    MODEL_7_EXIT_POLICY,
    MODEL_7_FAST_MA_PERIOD,
    MODEL_7_ID,
    MODEL_7_MINIMUM_DISTANCE_PERCENT,
    MODEL_7_MOMENTUM_PERIOD,
    MODEL_7_PROTECTION_ACTIVATION_RR,
    MODEL_7_RISK_REWARD,
    MODEL_7_SLOW_MA_PERIOD,
    MODEL_7_TIMEFRAME,
    MODEL_7_VOLATILITY_PERIOD,
    model7_trend_momentum_configuration,
    model7_trend_momentum_parameters,
)


class Model7TrendMomentumDynamicTest(unittest.TestCase):
    def test_entry_is_frozen_and_identity_is_independent(self) -> None:
        configuration = model7_trend_momentum_configuration()

        self.assertEqual(MODEL_7_ID, "MODELO_7_TREND_MOMENTUM_DYNAMIC")
        self.assertEqual(MODEL_7_ALPHA_ID, "ALPHA001")
        self.assertEqual(MODEL_7_TIMEFRAME, "M1")
        self.assertEqual(MODEL_7_CANDLES, 1000)
        self.assertEqual(configuration.fast_ma_period, MODEL_7_FAST_MA_PERIOD)
        self.assertEqual(configuration.slow_ma_period, MODEL_7_SLOW_MA_PERIOD)
        self.assertEqual(configuration.feature_lookback, MODEL_7_MOMENTUM_PERIOD)
        self.assertEqual(configuration.volatility_period, MODEL_7_VOLATILITY_PERIOD)

    def test_initial_risk_and_dynamic_protection_are_explicit(self) -> None:
        parameters = model7_trend_momentum_parameters()

        self.assertEqual(float(parameters["atr_stop_factor"]), MODEL_7_ATR_STOP_FACTOR)
        self.assertEqual(
            float(parameters["minimum_distance_percent"]),
            MODEL_7_MINIMUM_DISTANCE_PERCENT,
        )
        self.assertEqual(float(parameters["rr"]), MODEL_7_RISK_REWARD)
        self.assertEqual(parameters["beta_id"], MODEL_7_BETA_ID)
        self.assertEqual(parameters["beta_version"], MODEL_7_BETA_VERSION)
        self.assertEqual(parameters["stop_management"], MODEL_7_EXIT_POLICY)
        self.assertEqual(
            float(parameters["break_even_trigger_rr"]),
            MODEL_7_PROTECTION_ACTIVATION_RR,
        )
        self.assertEqual(
            float(parameters["atr_trailing_activation_rr"]),
            MODEL_7_PROTECTION_ACTIVATION_RR,
        )
        self.assertEqual(
            parameters["exit_contract"],
            "DYNAMIC_PROTECT_ONLY_NO_FULL_EXIT",
        )


if __name__ == "__main__":
    unittest.main()
