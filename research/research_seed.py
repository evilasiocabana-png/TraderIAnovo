"""Seed demonstrativa em memoria para pesquisa quantitativa."""

from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import MarketRegime, RegimeAnalysis


def build_demo_market_memory() -> MarketMemory:
    """Cria uma MarketMemory com cenarios simulados variados."""
    memory = MarketMemory()
    _remember(memory, MarketRegime.TREND, "UP", 10.0, "MEDIUM", 0.90)
    _remember(memory, MarketRegime.TREND, "UP", 11.0, "MEDIUM", 0.85)
    _remember(memory, MarketRegime.TREND, "DOWN", -10.0, "MEDIUM", 0.90)
    _remember(memory, MarketRegime.RANGE, "SIDEWAYS", 0.0, "LOW", 0.20)
    _remember(memory, MarketRegime.HIGH_VOLATILITY, "UP", 18.0, "HIGH", 0.75)
    _remember(
        memory,
        MarketRegime.LOW_VOLATILITY,
        "SIDEWAYS",
        0.0,
        "LOW",
        0.10,
    )
    return memory


def _remember(
    memory: MarketMemory,
    regime: MarketRegime,
    direction: str,
    momentum: float,
    volatility: str,
    trend_strength: float,
) -> None:
    feature_snapshot = FeatureSnapshot(
        momentum=momentum,
        average_range=10.0,
        highest_high=None,
        lowest_low=None,
        direction=direction,
        candles_count=20,
        trend_strength=trend_strength,
        volatility_level=volatility,
    )
    memory.remember(feature_snapshot, _regime_analysis(regime))


def _regime_analysis(regime: MarketRegime) -> RegimeAnalysis:
    return RegimeAnalysis(
        regime=regime,
        confidence=0.70,
        description="Cenario demonstrativo de pesquisa quantitativa.",
    )
