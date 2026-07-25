"""Frozen M7 Trend Momentum entry with an intentional dynamic protection exit."""

from __future__ import annotations

from research.quantitative_score_engine import QuantitativeScoreConfiguration


MODEL_7_ID = "MODELO_7_TREND_MOMENTUM_DYNAMIC"
MODEL_7_TIMEFRAME = "M1"
MODEL_7_ALPHA_ID = "ALPHA001"
MODEL_7_ALPHA_VERSION = "MARCO_ZERO_A3BC912"
MODEL_7_BETA_ID = "BETA007"
MODEL_7_BETA_VERSION = "BETA007_DYNAMIC_PROTECT_ONLY_V1"
MODEL_7_BETA_MODE = "PROTECT_ONLY"
MODEL_7_EXIT_POLICY = "M7_DYNAMIC_PROTECT_ONLY"
MODEL_7_CANDLES = 1000
MODEL_7_FAST_MA_PERIOD = 20
MODEL_7_SLOW_MA_PERIOD = 50
MODEL_7_MOMENTUM_PERIOD = 10
MODEL_7_VOLATILITY_PERIOD = 20
MODEL_7_RSI_PERIOD = 14
MODEL_7_RSI_OVERSOLD = 30.0
MODEL_7_RSI_OVERBOUGHT = 70.0
MODEL_7_VOLATILITY_MINIMUM = 0.00001
MODEL_7_MA_FLAT_THRESHOLD = 0.00005
MODEL_7_CONFIDENCE = 0.55
MODEL_7_ATR_STOP_FACTOR = 2.0
MODEL_7_MINIMUM_DISTANCE_PERCENT = 0.001
MODEL_7_RISK_REWARD = 2.0
MODEL_7_PROTECTION_ACTIVATION_RR = 1.5
MODEL_7_ATR_TRAILING_FACTOR = 2.0
MODEL_7_BREAK_EVEN_OFFSET_PIPS = 0.0


def model7_trend_momentum_configuration() -> QuantitativeScoreConfiguration:
    """Return the immutable M7 entry setup recovered from the original baseline."""
    return QuantitativeScoreConfiguration(
        candles_loaded=MODEL_7_CANDLES,
        feature_lookback=MODEL_7_MOMENTUM_PERIOD,
        forward_return_candles=1,
        fast_ma_period=MODEL_7_FAST_MA_PERIOD,
        slow_ma_period=MODEL_7_SLOW_MA_PERIOD,
        rsi_period=MODEL_7_RSI_PERIOD,
        volatility_period=MODEL_7_VOLATILITY_PERIOD,
        min_sample_size=1,
        min_profit_factor=0.0,
        min_win_rate=0.0,
        confidence_floor=MODEL_7_CONFIDENCE,
        confidence_ceiling=1.0,
        volatility_bucket_method="SIMPLE",
        volatility_low_threshold=MODEL_7_VOLATILITY_MINIMUM,
        volatility_high_threshold=1.0,
        ma_flat_threshold=MODEL_7_MA_FLAT_THRESHOLD,
        ma_strong_threshold=0.001,
        rsi_oversold_threshold=MODEL_7_RSI_OVERSOLD,
        rsi_overbought_threshold=MODEL_7_RSI_OVERBOUGHT,
    )


def model7_trend_momentum_parameters() -> dict[str, str]:
    """Return the complete M7 entry, initial-risk and protection contract."""
    return {
        "alpha": MODEL_7_ALPHA_ID,
        "alpha_version": MODEL_7_ALPHA_VERSION,
        "beta_id": MODEL_7_BETA_ID,
        "beta_version": MODEL_7_BETA_VERSION,
        "beta_mode": MODEL_7_BETA_MODE,
        "timeframe": MODEL_7_TIMEFRAME,
        "candles": str(MODEL_7_CANDLES),
        "fast_ma_period": str(MODEL_7_FAST_MA_PERIOD),
        "slow_ma_period": str(MODEL_7_SLOW_MA_PERIOD),
        "momentum_period": str(MODEL_7_MOMENTUM_PERIOD),
        "volatility_period": str(MODEL_7_VOLATILITY_PERIOD),
        "volatility_threshold": str(MODEL_7_VOLATILITY_MINIMUM),
        "rsi_period": str(MODEL_7_RSI_PERIOD),
        "rsi_oversold": str(MODEL_7_RSI_OVERSOLD),
        "rsi_overbought": str(MODEL_7_RSI_OVERBOUGHT),
        "ma_flat_threshold": str(MODEL_7_MA_FLAT_THRESHOLD),
        "atr_stop_factor": str(MODEL_7_ATR_STOP_FACTOR),
        "minimum_distance_percent": str(MODEL_7_MINIMUM_DISTANCE_PERCENT),
        "rr": str(MODEL_7_RISK_REWARD),
        "stop_management": MODEL_7_EXIT_POLICY,
        "break_even_trigger_rr": str(MODEL_7_PROTECTION_ACTIVATION_RR),
        "break_even_offset_pips": str(MODEL_7_BREAK_EVEN_OFFSET_PIPS),
        "atr_trailing_activation_rr": str(MODEL_7_PROTECTION_ACTIVATION_RR),
        "atr_trailing_factor": str(MODEL_7_ATR_TRAILING_FACTOR),
        "exit_contract": "DYNAMIC_PROTECT_ONLY_NO_FULL_EXIT",
    }
