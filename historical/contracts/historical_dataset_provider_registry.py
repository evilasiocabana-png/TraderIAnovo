"""Contrato para registry logico de providers historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_provider_descriptor import (
    HistoricalDatasetProviderDescriptor,
)


@dataclass(frozen=True)
class HistoricalDatasetProviderRegistry:
    """DTO imutavel para agrupar descritores de providers historicos."""

    registry_id: str
    registry_name: str
    providers: tuple[HistoricalDatasetProviderDescriptor, ...]
    total_providers: int
    registry_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.providers, tuple):
            raise TypeError(
                "providers must be a tuple[HistoricalDatasetProviderDescriptor, ...]"
            )
        if any(
            not isinstance(provider, HistoricalDatasetProviderDescriptor)
            for provider in self.providers
        ):
            raise TypeError(
                "providers must contain only HistoricalDatasetProviderDescriptor values"
            )
        if not isinstance(self.total_providers, int):
            raise TypeError("total_providers must be int")
        if self.total_providers < 0:
            raise ValueError("total_providers must be non-negative")
