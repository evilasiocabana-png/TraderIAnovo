"""Contrato read-only da estrutura de mercado."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketStructureSnapshot:
    """Resumo estrutural calculado a partir de candles."""

    symbol: str
    timeframe: str
    current_price: float
    candles_count: int
    donchian_period: int
    donchian_high: float
    donchian_low: float
    donchian_mid: float
    donchian_position: float
    pivot: float
    pivot_r1: float
    pivot_r2: float
    pivot_s1: float
    pivot_s2: float
    vwap: float
    distance_to_vwap: float
    z_score: float
    bollinger_period: int
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    bollinger_width: float
    bollinger_position: float
    tick_volume: int
    tick_volume_average: float
    relative_tick_volume: float
    current_spread: float
    average_spread: float
    spread_to_average_ratio: float
    estimated_slippage: float
    price_velocity: float
    session: str
    session_liquidity: str
    spread_blocked: bool
    spread_status: str
    support: float
    resistance: float
    swing_high: float
    swing_low: float
    relevant_high: float
    relevant_low: float
    current_range_high: float
    current_range_low: float
    current_range_size: float
    current_range_position: float
    range_breakout: str
    distance_to_support: float
    distance_to_resistance: float
    nearest_structure_level: float
    distance_to_nearest_structure: float
    structure_status: str
    regime: str
    trend_strength: float
    volatility_compression: float
    volatility_expansion: float
    fast_ema_period: int
    medium_ema_period: int
    slow_ema_period: int
    fast_ema: float
    medium_ema: float
    slow_ema: float
    distance_to_fast_ema: float
    distance_to_medium_ema: float
    distance_to_slow_ema: float
    current_timeframe_direction: str
    dominant_multi_timeframe_direction: str
    timeframe_directions: tuple[str, ...]
    confidence: float
