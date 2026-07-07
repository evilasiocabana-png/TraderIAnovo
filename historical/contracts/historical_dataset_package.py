"""Contrato para pacote logico de datasets historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_manifest import HistoricalDatasetManifest


@dataclass(frozen=True)
class HistoricalDatasetPackage:
    """DTO imutavel para agrupar manifests historicos como pacote logico."""

    package_id: str
    package_name: str
    package_description: str
    manifests: tuple[HistoricalDatasetManifest, ...]
    total_datasets: int
    package_version: str
    created_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.manifests, tuple):
            raise TypeError(
                "manifests must be a tuple[HistoricalDatasetManifest, ...]"
            )
        if any(
            not isinstance(manifest, HistoricalDatasetManifest)
            for manifest in self.manifests
        ):
            raise TypeError(
                "manifests must contain only HistoricalDatasetManifest values"
            )
        if not isinstance(self.total_datasets, int):
            raise TypeError("total_datasets must be int")
        if self.total_datasets < 0:
            raise ValueError("total_datasets must be non-negative")
