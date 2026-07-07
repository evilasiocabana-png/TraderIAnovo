"""Relatorio consolidado do Decision Lab."""

from __future__ import annotations

from dataclasses import dataclass

from decision.decision_assessment import DecisionAssessment
from decision.decision_quality_engine import DecisionQualityResult
from decision.decision_score_engine import DecisionScoreResult


@dataclass(frozen=True)
class DecisionReport:
    """Consolida resultados produzidos pelos componentes do Decision Lab."""

    assessment: DecisionAssessment
    score_result: DecisionScoreResult
    quality_result: DecisionQualityResult
    strategy_score: float
    market_score: float
    research_score: float
    final_score: float
    confidence_score: float
    consistency_score: float
    approval_score: float
    execution_time: float
