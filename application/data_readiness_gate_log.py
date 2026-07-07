"""Auditoria estruturada do Data Readiness Gate."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataReadinessGateLog:
    """Registro estruturado de avaliacao do readiness gate."""

    dataset_id: str
    evaluated_at: str
    requested_action: str
    readiness_status: str
    decision: str
    provider: str = "unknown"
    reasons: list[str] = field(default_factory=list)


class DataReadinessGateLogger(ABC):
    """Porta para registrar auditoria do readiness gate."""

    @abstractmethod
    def log(self, record: DataReadinessGateLog) -> None:
        """Registra uma avaliacao do gate."""

    @abstractmethod
    def list_logs(self) -> list[DataReadinessGateLog]:
        """Lista registros de auditoria."""


@dataclass
class InMemoryDataReadinessGateLogger(DataReadinessGateLogger):
    """Logger em memoria para auditoria do readiness gate."""

    records: list[DataReadinessGateLog] = field(default_factory=list)

    def log(self, record: DataReadinessGateLog) -> None:
        """Registra uma avaliacao em memoria."""
        self.records.append(record)

    def list_logs(self) -> list[DataReadinessGateLog]:
        """Retorna copia dos registros em memoria."""
        return list(self.records)
