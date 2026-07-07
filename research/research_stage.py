"""Modelos de estado do Research Pipeline."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ResearchStage(Enum):
    """Estados oficiais de uma etapa do pipeline de pesquisa."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class ResearchStageResult:
    """Representa o estado de execucao de uma etapa."""

    stage: ResearchStage
    started_at: datetime | None
    finished_at: datetime | None
    duration: float
    success: bool
    message: str
