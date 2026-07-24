"""Regression tests for the frozen M6 Trend Momentum baseline."""

import unittest

from application.model6_original_trend_momentum import (
    MODEL_6_ALPHA_ID,
    MODEL_6_ATR_STOP_FACTOR,
    MODEL_6_CANDLES,
    MODEL_6_FAST_MA_PERIOD,
    MODEL_6_MOMENTUM_PERIOD,
    MODEL_6_MINIMUM_DISTANCE_PERCENT,
    MODEL_6_RISK_REWARD,
    MODEL_6_SLOW_MA_PERIOD,
    MODEL_6_TIMEFRAME,
    MODEL_6_VOLATILITY_PERIOD,
    original_trend_momentum_configuration,
    original_trend_momentum_parameters,
)


class Model6OriginalTrendMomentumTest(unittest.TestCase):
    def test_configuration_freezes_original_entry_setup(self) -> None:
        configuration = original_trend_momentum_configuration()

        self.assertEqual(MODEL_6_ALPHA_ID, "ALPHA001")
        self.assertEqual(MODEL_6_TIMEFRAME, "M1")
        self.assertEqual(MODEL_6_CANDLES, 1000)
        self.assertEqual(configuration.fast_ma_period, MODEL_6_FAST_MA_PERIOD)
        self.assertEqual(configuration.slow_ma_period, MODEL_6_SLOW_MA_PERIOD)
        self.assertEqual(configuration.feature_lookback, MODEL_6_MOMENTUM_PERIOD)
        self.assertEqual(configuration.volatility_period, MODEL_6_VOLATILITY_PERIOD)
        self.assertEqual(configuration.rsi_period, 14)
        self.assertEqual(configuration.rsi_oversold_threshold, 30.0)
        self.assertEqual(configuration.rsi_overbought_threshold, 70.0)
        self.assertEqual(configuration.volatility_low_threshold, 0.00001)

    def test_initial_risk_and_exit_contract_are_explicit(self) -> None:
        parameters = original_trend_momentum_parameters()

        self.assertEqual(float(parameters["atr_stop_factor"]), MODEL_6_ATR_STOP_FACTOR)
        self.assertEqual(
            float(parameters["minimum_distance_percent"]),
            MODEL_6_MINIMUM_DISTANCE_PERCENT,
        )
        self.assertEqual(float(parameters["rr"]), MODEL_6_RISK_REWARD)
        self.assertEqual(parameters["beta_id"], "BETA001")
        self.assertEqual(parameters["beta_mode"], "FIXED_SL_TP")
        self.assertEqual(parameters["stop_management"], "RESEARCH_FIXED_SL_TP")
        self.assertEqual(parameters["exit_contract"], "INITIAL_SL_TP_FIRST_TOUCH")
        self.assertNotIn("atr_trailing_activation_rr", parameters)
        self.assertNotIn("break_even_trigger_rr", parameters)


if __name__ == "__main__":
    unittest.main()
