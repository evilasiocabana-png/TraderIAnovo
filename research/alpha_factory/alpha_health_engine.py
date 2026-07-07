"""Motor de saude institucional de uma Alpha."""

from __future__ import annotations

from dataclasses import dataclass

from research.alpha001_research_report import Alpha001ResearchResult
from research.campaigns.campaign_report import CampaignReport
from research.validation.experiment_validation_report import (
    ExperimentValidationReport,
)


@dataclass(frozen=True)
class AlphaHealthResult:
    """Resultado consolidado da avaliacao de saude de uma Alpha."""

    robustness_score: float
    reproducibility_score: float
    validation_score: float
    campaign_score: float
    health_score: float


@dataclass(frozen=True)
class AlphaHealthEngine:
    """Avalia saude da Alpha usando apenas resultados existentes."""

    def evaluate(
        self,
        research_result: Alpha001ResearchResult,
        campaign_report: CampaignReport,
        validation_report: ExperimentValidationReport,
    ) -> AlphaHealthResult:
        """Calcula scores institucionais sem recalcular metricas de pesquisa."""
        robustness_score = self._robustness_score(research_result)
        reproducibility_score = self._metadata_score(
            campaign_report,
            "reproducibility_score",
        )
        validation_score = self._validation_score(validation_report)
        campaign_score = self._score(campaign_report.campaign_success_rate)
        health_score = self._average(
            (
                robustness_score,
                reproducibility_score,
                validation_score,
                campaign_score,
            )
        )

        return AlphaHealthResult(
            robustness_score=robustness_score,
            reproducibility_score=reproducibility_score,
            validation_score=validation_score,
            campaign_score=campaign_score,
            health_score=health_score,
        )

    def _robustness_score(
        self,
        research_result: Alpha001ResearchResult,
    ) -> float:
        profit_factor_score = self._score(
            research_result.profit_factor.profit_factor / 2.0
        )
        win_rate_score = self._score(research_result.win_rate.win_rate)
        drawdown_score = self._score(
            1.0 - (research_result.drawdown.max_drawdown_percent / 100.0)
        )
        return self._average(
            (
                profit_factor_score,
                win_rate_score,
                drawdown_score,
            )
        )

    def _validation_score(
        self,
        validation_report: ExperimentValidationReport,
    ) -> float:
        if validation_report.total_rules <= 0:
            return 0.0
        return self._score(
            len(validation_report.passed_rules)
            / validation_report.total_rules
        )

    def _metadata_score(
        self,
        campaign_report: CampaignReport,
        key: str,
    ) -> float:
        value = campaign_report.metadata.get(key, 0.0)
        if not isinstance(value, (int, float)):
            return 0.0
        return self._score(float(value))

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return self._score(sum(values) / len(values))

    def _score(self, value: float) -> float:
        return max(0.0, min(1.0, value))
