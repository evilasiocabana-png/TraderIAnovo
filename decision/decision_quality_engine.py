"""Avaliador de qualidade do score de decisao."""

from dataclasses import dataclass
from math import isfinite

from decision.decision_score_engine import DecisionScoreResult


@dataclass(frozen=True)
class DecisionQualityResult:
    """Resultado de qualidade estatistica da decisao."""

    confidence_score: float
    consistency_score: float
    approval_score: float


@dataclass(frozen=True)
class DecisionQualityEngine:
    """Avalia qualidade sem produzir decisao operacional."""

    def evaluate(self, score_result: DecisionScoreResult) -> DecisionQualityResult:
        """Retorna scores de qualidade a partir dos scores consolidados."""
        confidence_score = self._normalize(score_result.final_score)
        consistency_score = self._consistency_score(score_result)
        approval_score = round((confidence_score + consistency_score) / 2, 2)
        return DecisionQualityResult(
            confidence_score=confidence_score,
            consistency_score=consistency_score,
            approval_score=approval_score,
        )

    def _consistency_score(self, score_result: DecisionScoreResult) -> float:
        scores = (
            self._normalize(score_result.strategy_score),
            self._normalize(score_result.market_score),
            self._normalize(score_result.research_score),
        )
        spread = max(scores) - min(scores)
        return round(100.0 - spread, 2)

    def _normalize(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value < 0:
            return 0.0
        if value > 100:
            return 100.0
        return round(value, 2)
