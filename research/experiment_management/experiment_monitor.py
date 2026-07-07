"""Monitoramento em memoria da execucao de experimentos."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal


ExperimentStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
]


@dataclass(frozen=True)
class ExperimentExecutionStatus:
    """Estado monitorado de uma execucao de experimento."""

    experiment_id: str
    status: ExperimentStatus
    started_at: datetime | None
    finished_at: datetime | None
    execution_time: float
    error_message: str


@dataclass
class ExperimentMonitor:
    """Registra status de experimentos sem executar pesquisas."""

    _statuses: dict[str, ExperimentExecutionStatus] = field(
        default_factory=dict,
        init=False,
    )

    def mark_pending(self, experiment_id: str) -> ExperimentExecutionStatus:
        """Registra um experimento pendente."""
        status = ExperimentExecutionStatus(
            experiment_id=experiment_id,
            status="pending",
            started_at=None,
            finished_at=None,
            execution_time=0.0,
            error_message="",
        )
        self._statuses[experiment_id] = status
        return status

    def mark_running(
        self,
        experiment_id: str,
        started_at: datetime | None = None,
    ) -> ExperimentExecutionStatus:
        """Registra inicio de execucao de um experimento."""
        status = ExperimentExecutionStatus(
            experiment_id=experiment_id,
            status="running",
            started_at=started_at or datetime.now(),
            finished_at=None,
            execution_time=0.0,
            error_message="",
        )
        self._statuses[experiment_id] = status
        return status

    def mark_completed(
        self,
        experiment_id: str,
        finished_at: datetime | None = None,
    ) -> ExperimentExecutionStatus:
        """Registra conclusao bem-sucedida de um experimento."""
        return self._finish(experiment_id, "completed", "", finished_at)

    def mark_failed(
        self,
        experiment_id: str,
        error_message: str,
        finished_at: datetime | None = None,
    ) -> ExperimentExecutionStatus:
        """Registra falha de um experimento."""
        return self._finish(experiment_id, "failed", error_message, finished_at)

    def mark_cancelled(
        self,
        experiment_id: str,
        error_message: str = "",
        finished_at: datetime | None = None,
    ) -> ExperimentExecutionStatus:
        """Registra cancelamento de um experimento."""
        return self._finish(experiment_id, "cancelled", error_message, finished_at)

    def get_status(self, experiment_id: str) -> ExperimentExecutionStatus | None:
        """Retorna o status registrado para um experimento."""
        return self._statuses.get(experiment_id)

    def list_statuses(self) -> tuple[ExperimentExecutionStatus, ...]:
        """Lista os status monitorados em memoria."""
        return tuple(self._statuses.values())

    def clear(self) -> None:
        """Remove todos os status monitorados."""
        self._statuses.clear()

    def _finish(
        self,
        experiment_id: str,
        status: ExperimentStatus,
        error_message: str,
        finished_at: datetime | None,
    ) -> ExperimentExecutionStatus:
        previous = self._statuses.get(experiment_id)
        finished = finished_at or datetime.now()
        started_at = previous.started_at if previous else None
        execution_time = self._execution_time(started_at, finished)
        if previous is None:
            result = ExperimentExecutionStatus(
                experiment_id=experiment_id,
                status=status,
                started_at=None,
                finished_at=finished,
                execution_time=0.0,
                error_message=error_message,
            )
        else:
            result = replace(
                previous,
                status=status,
                finished_at=finished,
                execution_time=execution_time,
                error_message=error_message,
            )
        self._statuses[experiment_id] = result
        return result

    def _execution_time(
        self,
        started_at: datetime | None,
        finished_at: datetime,
    ) -> float:
        if started_at is None:
            return 0.0
        return max((finished_at - started_at).total_seconds(), 0.0)
