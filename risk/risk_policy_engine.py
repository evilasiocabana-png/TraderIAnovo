"""Aplicacao de politicas quantitativas de risco."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreResult


RiskPolicyDecision = Literal[
    "ALLOW",
    "REDUCE",
    "BLOCK_RESEARCH",
    "BLOCK_PAPER",
]


@dataclass(frozen=True)
class RiskPolicyResult:
    """Resultado de politica quantitativa sem execucao operacional."""

    decision: RiskPolicyDecision
    reason: str
    final_risk_score: float


@dataclass(frozen=True)
class RiskPolicyEngine:
    """Aplica politica quantitativa sem enviar ou aprovar ordens."""

    def evaluate(
        self,
        profile: RiskProfile,
        score_result: RiskScoreResult,
    ) -> RiskPolicyResult:
        """Retorna a decisao de politica para pesquisa e paper trading."""
        final_score = self._score(score_result.final_risk_score)

        if not profile.enabled:
            return RiskPolicyResult(
                decision="BLOCK_PAPER",
                reason="Perfil de risco desabilitado.",
                final_risk_score=final_score,
            )

        if self._requires_research_block(score_result, final_score):
            return RiskPolicyResult(
                decision="BLOCK_RESEARCH",
                reason="Score insuficiente para continuidade da pesquisa.",
                final_risk_score=final_score,
            )

        if self._requires_paper_block(score_result, final_score):
            return RiskPolicyResult(
                decision="BLOCK_PAPER",
                reason="Risco quantitativo incompativel com paper trading.",
                final_risk_score=final_score,
            )

        if final_score < 75.0:
            return RiskPolicyResult(
                decision="REDUCE",
                reason="Risco quantitativo requer reducao de exposicao.",
                final_risk_score=final_score,
            )

        return RiskPolicyResult(
            decision="ALLOW",
            reason="Politica quantitativa dentro dos limites definidos.",
            final_risk_score=final_score,
        )

    def _requires_research_block(
        self,
        score_result: RiskScoreResult,
        final_score: float,
    ) -> bool:
        return final_score < 25.0 or score_result.research_score < 25.0

    def _requires_paper_block(
        self,
        score_result: RiskScoreResult,
        final_score: float,
    ) -> bool:
        minimum_component_score = min(
            score_result.exposure_score,
            score_result.drawdown_score,
            score_result.volatility_score,
        )
        return final_score < 50.0 or minimum_component_score < 40.0

    def _score(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value < 0:
            return 0.0
        if value > 100:
            return 100.0
        return round(value, 2)
