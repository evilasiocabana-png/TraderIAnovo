"""Porta de persistencia para qualidade de datasets historicos."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class HistoricalDatasetQualityStatus:
    """Snapshot persistivel de metadados e qualidade sem candles."""

    dataset_id: str
    ativo: str
    timeframe: str
    provider: str
    start_date: str | None
    end_date: str | None
    total_candles: int
    quality_status: str
    errors: list[str] = field(default_factory=list)
    last_validated_at: str = ""


@dataclass(frozen=True)
class HistoricalDatasetQualityValidationRecord:
    """Registro historico de uma validacao de qualidade."""

    dataset_id: str
    validated_at: str
    quality_status: str
    total_candles: int
    invalid_ohlc_candles: int = 0
    invalid_volume_candles: int = 0
    temporal_gaps: int = 0
    duplicate_timestamps: int = 0
    messages: list[str] = field(default_factory=list)


class HistoricalDatasetQualityRepository(ABC):
    """Contrato para persistir status de qualidade historica."""

    @abstractmethod
    def save(self, status: HistoricalDatasetQualityStatus) -> None:
        """Persiste ou atualiza o ultimo status conhecido."""

    @abstractmethod
    def get(self, dataset_id: str) -> HistoricalDatasetQualityStatus | None:
        """Busca o ultimo status conhecido de um dataset."""

    @abstractmethod
    def list_all(self) -> list[HistoricalDatasetQualityStatus]:
        """Lista todos os status persistidos."""

    @abstractmethod
    def append_validation(
        self,
        record: HistoricalDatasetQualityValidationRecord,
    ) -> None:
        """Registra uma execucao de validacao de qualidade."""

    @abstractmethod
    def list_validations(
        self,
        dataset_id: str,
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        """Lista historico de validacoes por dataset."""
