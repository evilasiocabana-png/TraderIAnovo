"""Relatorio consolidado de execucao de experimento."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_monitor import ExperimentExecutionStatus
from research.research_execution_result import ResearchExecutionResult


@dataclass(frozen=True)
class ExperimentReport:
    """Consolida informacoes produzidas pela execucao de experimento."""

    definition: ExperimentDefinition
    execution_status: ExperimentExecutionStatus
    execution_result: ResearchExecutionResult
    experiment_id: str
    alpha_id: str
    status: str
    execution_time: float
    success: bool
    total_errors: int
    recommendation: str
    metadata: Mapping[str, object]
