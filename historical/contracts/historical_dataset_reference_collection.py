"""Contrato para colecao logica de referencias historicas."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_reference import HistoricalDatasetReference


@dataclass(frozen=True)
class HistoricalDatasetReferenceCollection:
    """DTO imutavel para transportar referencias leves de datasets historicos."""

    collection_id: str
    collection_name: str
    references: tuple[HistoricalDatasetReference, ...]
    total_references: int
    created_at: str
    collection_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple):
            raise TypeError(
                "references must be a tuple[HistoricalDatasetReference, ...]"
            )
        if any(
            not isinstance(reference, HistoricalDatasetReference)
            for reference in self.references
        ):
            raise TypeError(
                "references must contain only HistoricalDatasetReference values"
            )
        if not isinstance(self.total_references, int):
            raise TypeError("total_references must be int")
        if self.total_references < 0:
            raise ValueError("total_references must be non-negative")
