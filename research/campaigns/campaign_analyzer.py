"""Analise agregada de campanhas de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass

from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage


@dataclass(frozen=True)
class CampaignAnalysisResult:
    """Resultado agregado da analise de uma campanha."""

    total_experiments: int
    successful_experiments: int
    failed_experiments: int
    approved_experiments: int
    rejected_experiments: int
    average_execution_time: float
    campaign_success_rate: float


@dataclass(frozen=True)
class CampaignAnalyzer:
    """Calcula indicadores agregados a partir de execucoes de pesquisa."""

    def analyze(
        self,
        results: tuple[ResearchExecutionResult, ...],
    ) -> CampaignAnalysisResult:
        """Consolida estatisticas da campanha sem recalcular metricas individuais."""
        total = len(results)
        successful = sum(1 for result in results if self._is_success(result))
        failed = total - successful
        approved = sum(1 for result in results if self._is_approved(result))
        rejected = sum(1 for result in results if self._is_rejected(result))
        average_time = (
            sum(result.duration for result in results) / total
            if total
            else 0.0
        )
        success_rate = successful / total if total else 0.0

        return CampaignAnalysisResult(
            total_experiments=total,
            successful_experiments=successful,
            failed_experiments=failed,
            approved_experiments=approved,
            rejected_experiments=rejected,
            average_execution_time=average_time,
            campaign_success_rate=success_rate,
        )

    def _is_success(self, result: ResearchExecutionResult) -> bool:
        return result.status == ResearchStage.COMPLETED and not result.errors

    def _is_approved(self, result: ResearchExecutionResult) -> bool:
        return (
            result.validation.approved
            or result.recommendation.recommendation == "APPROVED_FOR_MORE_RESEARCH"
        )

    def _is_rejected(self, result: ResearchExecutionResult) -> bool:
        return result.recommendation.recommendation == "REJECTED"
