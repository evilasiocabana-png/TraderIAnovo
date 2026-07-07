"""Contrato para registry logico de origens historicas."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_source_descriptor import (
    HistoricalDatasetSourceDescriptor,
)


@dataclass(frozen=True)
class HistoricalDatasetSourceRegistry:
    """DTO imutavel para agrupar descritores de origens historicas."""

    registry_id: str
    registry_name: str
    sources: tuple[HistoricalDatasetSourceDescriptor, ...]
    total_sources: int
    registry_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.sources, tuple):
            raise TypeError(
                "sources must be a tuple[HistoricalDatasetSourceDescriptor, ...]"
            )
        if any(
            not isinstance(source, HistoricalDatasetSourceDescriptor)
            for source in self.sources
        ):
            raise TypeError(
                "sources must contain only HistoricalDatasetSourceDescriptor values"
            )
        if not isinstance(self.total_sources, int):
            raise TypeError("total_sources must be int")
        if self.total_sources < 0:
            raise ValueError("total_sources must be non-negative")
