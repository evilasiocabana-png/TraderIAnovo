"""Frozen configuration for the original Forex Trend Momentum model."""

from __future__ import annotations

from research.quantitative_score_engine import QuantitativeScoreConfiguration


MODEL_6_ID = "MODELO_6_TREND_MOMENTUM_ORIGINAL"
MODEL_6_LEGACY_ID = "MODELO_6_ESPELHO_M5"
MODEL_6_TIMEFRAME = "M1"
MODEL_6_ALPHA_ID = "ALPHA001"
MODEL_6_ALPHA_VERSION = "MARCO_ZERO_A3BC912"
MODEL_6_BETA_ID = "BETA001"
MODEL_6_BETA_VERSION = "BETA001_FIXED_SL_TP_RR2_V1"
MODEL_6_EXIT_POLICY = "RESEARCH_FIXED_SL_TP"
MODEL_6_CANDLES = 1000
MODEL_6_FAST_MA_PERIOD = 20
MODEL_6_SLOW_MA_PERIOD = 50
MODEL_6_MOMENTUM_PERIOD = 10
MODEL_6_VOLATILITY_PERIOD = 20
MODEL_6_RSI_PERIOD = 14
MODEL_6_RSI_OVERSOLD = 30.0
MODEL_6_RSI_OVERBOUGHT = 70.0
MODEL_6_VOLATILITY_MINIMUM = 0.00001
MODEL_6_MA_FLAT_THRESHOLD = 0.00005
MODEL_6_CONFIDENCE = 0.55
MODEL_6_ATR_STOP_FACTOR = 2.0
MODEL_6_MINIMUM_DISTANCE_PERCENT = 0.001
MODEL_6_RISK_REWARD = 2.0


def original_trend_momentum_configuration() -> QuantitativeScoreConfiguration:
    """Return the immutable signal configuration recovered from the baseline."""
    return QuantitativeScoreConfiguration(
        candles_loaded=MODEL_6_CANDLES,
        feature_lookback=MODEL_6_MOMENTUM_PERIOD,
        forward_return_candles=1,
        fast_ma_period=MODEL_6_FAST_MA_PERIOD,
        slow_ma_period=MODEL_6_SLOW_MA_PERIOD,
        rsi_period=MODEL_6_RSI_PERIOD,
        volatility_period=MODEL_6_VOLATILITY_PERIOD,
        min_sample_size=1,
        min_profit_factor=0.0,
        min_win_rate=0.0,
        confidence_floor=MODEL_6_CONFIDENCE,
        confidence_ceiling=1.0,
        volatility_bucket_method="SIMPLE",
        volatility_low_threshold=MODEL_6_VOLATILITY_MINIMUM,
        volatility_high_threshold=1.0,
        ma_flat_threshold=MODEL_6_MA_FLAT_THRESHOLD,
        ma_strong_threshold=0.001,
        rsi_oversold_threshold=MODEL_6_RSI_OVERSOLD,
        rsi_overbought_threshold=MODEL_6_RSI_OVERBOUGHT,
    )


def original_trend_momentum_parameters() -> dict[str, str]:
    """Return all frozen entry and initial-risk parameters for audit snapshots."""
    return {
        "alpha": MODEL_6_ALPHA_ID,
        "alpha_version": MODEL_6_ALPHA_VERSION,
        "beta_id": MODEL_6_BETA_ID,
        "beta_version": MODEL_6_BETA_VERSION,
        "beta_mode": "FIXED_SL_TP",
        "timeframe": MODEL_6_TIMEFRAME,
        "candles": str(MODEL_6_CANDLES),
        "fast_ma_period": str(MODEL_6_FAST_MA_PERIOD),
        "slow_ma_period": str(MODEL_6_SLOW_MA_PERIOD),
        "momentum_period": str(MODEL_6_MOMENTUM_PERIOD),
        "volatility_period": str(MODEL_6_VOLATILITY_PERIOD),
        "volatility_threshold": str(MODEL_6_VOLATILITY_MINIMUM),
        "rsi_period": str(MODEL_6_RSI_PERIOD),
        "rsi_oversold": str(MODEL_6_RSI_OVERSOLD),
        "rsi_overbought": str(MODEL_6_RSI_OVERBOUGHT),
        "ma_flat_threshold": str(MODEL_6_MA_FLAT_THRESHOLD),
        "atr_stop_factor": str(MODEL_6_ATR_STOP_FACTOR),
        "minimum_distance_percent": str(MODEL_6_MINIMUM_DISTANCE_PERCENT),
        "rr": str(MODEL_6_RISK_REWARD),
        "stop_management": MODEL_6_EXIT_POLICY,
        "exit_contract": "INITIAL_SL_TP_FIRST_TOUCH",
    }
