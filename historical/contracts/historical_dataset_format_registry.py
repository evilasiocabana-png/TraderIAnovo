"""Contrato para registry logico de formatos historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_format_descriptor import (
    HistoricalDatasetFormatDescriptor,
)


@dataclass(frozen=True)
class HistoricalDatasetFormatRegistry:
    """DTO imutavel para agrupar descritores de formatos historicos."""

    registry_id: str
    registry_name: str
    supported_formats: tuple[HistoricalDatasetFormatDescriptor, ...]
    total_formats: int
    registry_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.supported_formats, tuple):
            raise TypeError(
                "supported_formats must be a tuple[HistoricalDatasetFormatDescriptor, ...]"
            )
        if any(
            not isinstance(format_descriptor, HistoricalDatasetFormatDescriptor)
            for format_descriptor in self.supported_formats
        ):
            raise TypeError(
                "supported_formats must contain only HistoricalDatasetFormatDescriptor values"
            )
        if not isinstance(self.total_formats, int):
            raise TypeError("total_formats must be int")
        if self.total_formats < 0:
            raise ValueError("total_formats must be non-negative")
