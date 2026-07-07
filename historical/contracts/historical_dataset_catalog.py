"""Contrato para catalogo logico de datasets historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_catalog_entry import (
    HistoricalDatasetCatalogEntry,
)


@dataclass(frozen=True)
class HistoricalDatasetCatalog:
    """DTO imutavel para agrupar entradas de catalogo historico."""

    catalog_id: str
    catalog_name: str
    entries: tuple[HistoricalDatasetCatalogEntry, ...]
    total_datasets: int
    catalog_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError(
                "entries must be a tuple[HistoricalDatasetCatalogEntry, ...]"
            )
        if any(not isinstance(entry, HistoricalDatasetCatalogEntry) for entry in self.entries):
            raise TypeError(
                "entries must contain only HistoricalDatasetCatalogEntry values"
            )
        if not isinstance(self.total_datasets, int):
            raise TypeError("total_datasets must be int")
        if self.total_datasets < 0:
            raise ValueError("total_datasets must be non-negative")
