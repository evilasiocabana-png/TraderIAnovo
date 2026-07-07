"""Contrato para registry logico de identidades historicas."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_identity import HistoricalDatasetIdentity


@dataclass(frozen=True)
class HistoricalDatasetIdentityRegistry:
    """DTO imutavel para agrupar identidades logicas de datasets historicos."""

    registry_id: str
    registry_name: str
    identities: tuple[HistoricalDatasetIdentity, ...]
    total_datasets: int
    registry_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.identities, tuple):
            raise TypeError(
                "identities must be a tuple[HistoricalDatasetIdentity, ...]"
            )
        if any(
            not isinstance(identity, HistoricalDatasetIdentity)
            for identity in self.identities
        ):
            raise TypeError(
                "identities must contain only HistoricalDatasetIdentity values"
            )
        if not isinstance(self.total_datasets, int):
            raise TypeError("total_datasets must be int")
        if self.total_datasets < 0:
            raise ValueError("total_datasets must be non-negative")
