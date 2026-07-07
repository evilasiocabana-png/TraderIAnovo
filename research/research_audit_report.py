"""Relatorio oficial de auditoria do Research Lab."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from research.experiment_version_manager import ExperimentVersion
from research.research_execution_result import ResearchExecutionResult


@dataclass(frozen=True)
class ResearchAuditReport:
    """Consolida informacoes auditaveis de uma execucao de pesquisa."""

    experiment_id: str
    version: int
    alpha_name: str
    architecture_version: str
    execution_date: datetime | None
    configuration_hash: str
    pipeline_steps: tuple[str, ...]
    execution_time: float
    final_status: str
    recommendation: str

    @classmethod
    def from_execution(
        cls,
        execution_result: ResearchExecutionResult,
        experiment_version: ExperimentVersion,
        alpha_name: str | None = None,
        architecture_version: str = "research-lab-v1",
    ) -> "ResearchAuditReport":
        """Cria um relatorio consolidando resultado e versao."""
        return cls(
            experiment_id=experiment_version.experiment_id,
            version=experiment_version.version,
            alpha_name=alpha_name or cls._alpha_name(execution_result),
            architecture_version=architecture_version,
            execution_date=(
                execution_result.started_at
                or execution_result.finished_at
                or experiment_version.created_at
            ),
            configuration_hash=experiment_version.configuration_hash,
            pipeline_steps=tuple(
                stage_result.message
                for stage_result in execution_result.stage_results
            ),
            execution_time=execution_result.duration,
            final_status=execution_result.status.value,
            recommendation=execution_result.recommendation.recommendation,
        )

    @staticmethod
    def _alpha_name(execution_result: ResearchExecutionResult) -> str:
        for source in (
            execution_result,
            execution_result.experiment,
            execution_result.research_report,
        ):
            value = ResearchAuditReport._attribute_value(
                source,
                ("alpha_name", "alpha", "alpha_id"),
            )
            if value:
                return value
        return "Alpha001"

    @staticmethod
    def _attribute_value(source: Any, names: tuple[str, ...]) -> str | None:
        for name in names:
            value = getattr(source, name, None)
            if value:
                return str(value)
        return None
