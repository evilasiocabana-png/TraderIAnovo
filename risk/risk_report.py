"""Relatorio oficial do Risk Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from risk.risk_policy_engine import RiskPolicyResult
from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreResult


@dataclass(frozen=True)
class RiskReport:
    """Consolida resultados produzidos pelo Risk Lab."""

    profile: RiskProfile
    score_result: RiskScoreResult
    policy_result: RiskPolicyResult
    capital: float
    max_exposure: float
    final_risk_score: float
    policy_decision: str
    exposure_score: float
    drawdown_score: float
    volatility_score: float
    research_score: float
    execution_time: float
    metadata: Mapping[str, object]
