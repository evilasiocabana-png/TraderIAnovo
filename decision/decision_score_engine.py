"""Calculo isolado do score consolidado de decisao."""

from dataclasses import dataclass
from math import isfinite

from decision.decision_assessment import DecisionAssessment


@dataclass(frozen=True)
class DecisionScoreResult:
    """Resultado de score consolidado da decisao."""

    strategy_score: float
    market_score: float
    research_score: float
    final_score: float


@dataclass(frozen=True)
class DecisionScoreEngine:
    """Calcula scores a partir de DecisionAssessment."""

    def calculate(self, assessment: DecisionAssessment) -> DecisionScoreResult:
        """Retorna score consolidado sem aprovar decisao."""
        strategy_score = self._normalize_score(assessment.strategy_confidence)
        market_score = self._normalize_score(assessment.market_confidence)
        research_score = self._normalize_score(assessment.research_confidence)
        final_score = round(
            (strategy_score + market_score + research_score) / 3,
            2,
        )
        return DecisionScoreResult(
            strategy_score=strategy_score,
            market_score=market_score,
            research_score=research_score,
            final_score=final_score,
        )

    def _normalize_score(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value <= 0:
            return 0.0
        if value <= 1:
            return round(value * 100, 2)
        if value > 100:
            return 100.0
        return round(value, 2)
