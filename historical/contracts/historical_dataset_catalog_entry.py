"""Contrato para entrada de catalogo de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetCatalogEntry:
    """DTO imutavel para representar uma entrada de catalogo historico."""

    dataset_id: str
    dataset_name: str
    provider_name: str
    symbol: str
    timeframe: str
    start_timestamp: str
    end_timestamp: str
    record_count: int
    validation_status: str
    cataloged_at: str
    metadata_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.record_count, int):
            raise TypeError("record_count must be int")
        if self.record_count < 0:
            raise ValueError("record_count must be non-negative")
