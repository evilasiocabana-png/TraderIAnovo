"""Servico de aplicacao para pesquisa quantitativa."""

from dataclasses import dataclass

from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import RegimeAnalysis
from research.research_engine import ResearchEngine


@dataclass(frozen=True)
class ResearchData:
    """Dados de pesquisa prontos para consumo da aplicacao."""

    similar_scenarios: int
    confidence: float
    historical_score: float
    average_momentum: float
    average_trend_strength: float
    history_strength: str
    summary: str


@dataclass(frozen=True)
class ResearchService:
    """Expoe o ResearchEngine sem acoplar consumidores ao motor."""

    research_engine: ResearchEngine = ResearchEngine()

    def analyze(
        self,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        market_memory: MarketMemory,
    ) -> ResearchData:
        """Analisa dados de mercado e retorna DTO de aplicacao."""
        result = self.research_engine.analyze(
            feature_snapshot,
            regime_analysis,
            market_memory,
        )
        return ResearchData(
            similar_scenarios=result.similar_scenarios,
            confidence=result.confidence,
            historical_score=result.historical_score,
            average_momentum=result.average_momentum,
            average_trend_strength=result.average_trend_strength,
            history_strength=result.history_strength,
            summary=result.summary,
        )
