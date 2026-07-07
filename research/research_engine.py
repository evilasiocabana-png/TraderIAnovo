"""Motor de pesquisa quantitativa de cenarios de mercado."""

from dataclasses import dataclass

from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory, MarketMemoryRecord
from market.regime_engine import RegimeAnalysis


@dataclass(frozen=True)
class ResearchResult:
    """Resultado estatistico de pesquisa sobre cenarios similares."""

    similar_scenarios: int
    confidence: float
    historical_score: float
    average_momentum: float
    average_trend_strength: float
    history_strength: str
    summary: str


@dataclass(frozen=True)
class ResearchEngine:
    """Calcula qualidade estatistica sem gerar sinais ou ordens."""

    def analyze(
        self,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        market_memory: MarketMemory,
    ) -> ResearchResult:
        """Analisa cenarios similares usando apenas a memoria de mercado."""
        scenarios = market_memory.find_similar(
            feature_snapshot,
            regime_analysis,
        )
        count = len(scenarios)
        confidence = self._confidence(count)

        return ResearchResult(
            similar_scenarios=count,
            confidence=confidence,
            historical_score=confidence,
            average_momentum=self._average_momentum(scenarios),
            average_trend_strength=self._average_trend_strength(scenarios),
            history_strength=self._history_strength(count),
            summary=self._summary(count, confidence),
        )

    def _confidence(self, similar_scenarios: int) -> float:
        if similar_scenarios <= 0:
            return 0.0
        if similar_scenarios > 100:
            return 100.0
        return float(similar_scenarios)

    def _average_momentum(
        self,
        scenarios: list[MarketMemoryRecord],
    ) -> float:
        if not scenarios:
            return 0.0
        return sum(record.momentum for record in scenarios) / len(scenarios)

    def _average_trend_strength(
        self,
        scenarios: list[MarketMemoryRecord],
    ) -> float:
        if not scenarios:
            return 0.0
        total = sum(record.trend_strength for record in scenarios)
        return total / len(scenarios)

    def _history_strength(self, similar_scenarios: int) -> str:
        if similar_scenarios == 0:
            return "Sem historico"
        if similar_scenarios <= 9:
            return "Historico fraco"
        if similar_scenarios <= 49:
            return "Historico moderado"
        return "Historico forte"

    def _summary(self, similar_scenarios: int, confidence: float) -> str:
        strength = self._history_strength(similar_scenarios)
        if similar_scenarios == 0:
            return (
                "Nenhum cenario parecido foi encontrado. "
                "A confianca historica e 0.00, portanto o historico "
                "e inexistente. Quando aparecerem dados no dashboard, "
                "eles podem ser demonstrativos ate existir memoria real."
            )
        return (
            f"Foram encontrados {similar_scenarios} cenarios parecidos. "
            f"A confianca historica e {confidence:.2f}. "
            f"A forca do historico e: {strength}. "
            "Os dados podem ser demonstrativos quando nao houver "
            "memoria real conectada."
        )
