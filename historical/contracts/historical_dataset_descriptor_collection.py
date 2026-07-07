"""Contrato para colecao de descritores historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_descriptor import HistoricalDatasetDescriptor


@dataclass(frozen=True)
class HistoricalDatasetDescriptorCollection:
    """DTO imutavel para transportar descritores completos de datasets."""

    collection_id: str
    collection_name: str
    descriptors: tuple[HistoricalDatasetDescriptor, ...]
    total_descriptors: int
    created_at: str
    collection_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.descriptors, tuple):
            raise TypeError(
                "descriptors must be a tuple[HistoricalDatasetDescriptor, ...]"
            )
        if any(
            not isinstance(descriptor, HistoricalDatasetDescriptor)
            for descriptor in self.descriptors
        ):
            raise TypeError(
                "descriptors must contain only HistoricalDatasetDescriptor values"
            )
        if not isinstance(self.total_descriptors, int):
            raise TypeError("total_descriptors must be int")
        if self.total_descriptors < 0:
            raise ValueError("total_descriptors must be non-negative")
