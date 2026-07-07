"""Motor independente de classificacao de regime de mercado."""

from dataclasses import dataclass
from enum import Enum

from domain.contracts.market_snapshot import MarketSnapshot


class MarketRegime(Enum):
    """Regimes de mercado reconhecidos pelo TraderIA_WDO."""

    TREND = "TREND"
    RANGE = "RANGE"
    BREAKOUT = "BREAKOUT"
    NEWS = "NEWS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegimeAnalysis:
    """Resultado da classificacao de regime de mercado."""

    regime: MarketRegime
    confidence: float
    description: str


@dataclass(frozen=True)
class RegimeEngine:
    """Classifica o regime atual sem gerar sinais operacionais."""

    high_volatility_threshold: float = 80.0
    low_volatility_threshold: float = 15.0
    low_liquidity_threshold: float = 500.0
    trend_strength_threshold: float = 0.70

    def analyze(self, market_snapshot: MarketSnapshot) -> RegimeAnalysis:
        """Classifica o regime com regras simples e deterministicas."""
        if market_snapshot.liquidity <= self.low_liquidity_threshold:
            return self._analysis(MarketRegime.LOW_LIQUIDITY, 0.85)

        if market_snapshot.volatility >= self.high_volatility_threshold:
            return self._analysis(MarketRegime.HIGH_VOLATILITY, 0.80)

        if market_snapshot.volatility <= self.low_volatility_threshold:
            return self._analysis(MarketRegime.LOW_VOLATILITY, 0.75)

        if market_snapshot.trend_strength >= self.trend_strength_threshold:
            return self._analysis(MarketRegime.TREND, 0.70)

        if market_snapshot.regime.upper() == "RANGE":
            return self._analysis(MarketRegime.RANGE, 0.65)

        return self._analysis(MarketRegime.UNKNOWN, 0.30)

    def _analysis(self, regime: MarketRegime, confidence: float) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=regime,
            confidence=confidence,
            description=self._description(regime),
        )

    def _description(self, regime: MarketRegime) -> str:
        descriptions = {
            MarketRegime.TREND: "Mercado com predominancia direcional.",
            MarketRegime.RANGE: "Mercado lateralizado e sem expansao clara.",
            MarketRegime.BREAKOUT: "Mercado em rompimento.",
            MarketRegime.NEWS: "Mercado potencialmente afetado por noticia.",
            MarketRegime.HIGH_VOLATILITY: "Mercado com volatilidade elevada.",
            MarketRegime.LOW_VOLATILITY: "Mercado com volatilidade reduzida.",
            MarketRegime.LOW_LIQUIDITY: "Mercado com liquidez reduzida.",
            MarketRegime.UNKNOWN: "Regime de mercado indefinido.",
        }
        return descriptions[regime]
