"""Advisor de pesquisa para a Alpha 001 IORB."""

from dataclasses import dataclass

from research.alpha001_experiment_validator import Alpha001ValidationResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult


@dataclass(frozen=True)
class Alpha001ResearchAdvice:
    """Recomendacao de pesquisa derivada da validacao Alpha 001."""

    recommendation: str
    priority: str
    reasons: list[str]


@dataclass(frozen=True)
class Alpha001ResearchRecommendation:
    """Recomendacao de pesquisa derivada da validacao estatistica."""

    recommendation: str
    status: str
    reasons: tuple[str, ...]
    real_trading_authorized: bool = False


@dataclass(frozen=True)
class Alpha001ResearchAdvisor:
    """Interpreta validacao sem executar replay, backtest ou estrategia."""

    def recommend(
        self,
        validation_result: Alpha001ResearchValidationResult,
    ) -> Alpha001ResearchRecommendation:
        """Interpreta validacao estatistica sem sugerir operacao real."""
        recommendation = self._research_recommendation(validation_result)
        return Alpha001ResearchRecommendation(
            recommendation=recommendation,
            status=validation_result.status,
            reasons=tuple(validation_result.reasons),
            real_trading_authorized=False,
        )

    def analyze(
        self,
        validation_result: Alpha001ValidationResult,
    ) -> Alpha001ResearchAdvice:
        """Gera recomendacao de pesquisa a partir do resultado validado."""
        recommendations = self._recommendations(validation_result)
        priority = self._priority(recommendations)
        return Alpha001ResearchAdvice(
            recommendation=", ".join(recommendations),
            priority=priority,
            reasons=list(validation_result.reasons),
        )

    def _research_recommendation(
        self,
        validation_result: Alpha001ResearchValidationResult,
    ) -> str:
        if validation_result.status in {
            "INSUFFICIENT_SAMPLE",
            "INSUFFICIENT_TRADES",
        }:
            return "INSUFFICIENT_SAMPLE"
        if validation_result.approved:
            return "APPROVED_FOR_MORE_RESEARCH"
        return "REJECTED"

    def _recommendations(
        self,
        validation_result: Alpha001ValidationResult,
    ) -> list[str]:
        recommendations = [self._recommendation_for_status(validation_result.status)]
        recommendations.extend(
            self._recommendation_for_reason(reason)
            for reason in validation_result.reasons
            if self._recommendation_for_reason(reason) is not None
        )
        return self._deduplicate(recommendations)

    def _recommendation_for_status(self, status: str) -> str:
        mapping = {
            "APPROVED": "READY_FOR_EXTENDED_RESEARCH",
            "INSUFFICIENT_SAMPLE": "COLLECT_MORE_SAMPLES",
            "LOW_PROFIT_FACTOR": "REVIEW_ENTRY_FILTERS",
            "HIGH_DRAWDOWN": "REVIEW_RISK_PARAMETERS",
        }
        return mapping.get(status, "REVIEW_EXPERIMENT")

    def _recommendation_for_reason(self, reason: str) -> str | None:
        normalized = reason.lower()
        if "poucas operacoes" in normalized:
            return "COLLECT_MORE_SAMPLES"
        if "profit factor" in normalized:
            return "REVIEW_ENTRY_FILTERS"
        if "drawdown" in normalized:
            return "REVIEW_RISK_PARAMETERS"
        return None

    def _priority(self, recommendations: list[str]) -> str:
        priorities = {
            "REVIEW_RISK_PARAMETERS": "HIGH",
            "COLLECT_MORE_SAMPLES": "MEDIUM",
            "REVIEW_ENTRY_FILTERS": "MEDIUM",
            "REVIEW_EXPERIMENT": "MEDIUM",
            "READY_FOR_EXTENDED_RESEARCH": "LOW",
        }
        ordered = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return max(
            (priorities[recommendation] for recommendation in recommendations),
            key=lambda priority: ordered[priority],
        )

    def _deduplicate(self, recommendations: list[str | None]) -> list[str]:
        unique: list[str] = []
        for recommendation in recommendations:
            if recommendation is None:
                continue
            if recommendation not in unique:
                unique.append(recommendation)
        return unique
