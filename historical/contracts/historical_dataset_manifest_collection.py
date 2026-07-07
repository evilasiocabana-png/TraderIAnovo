"""Contrato para colecao de manifests historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_manifest import HistoricalDatasetManifest


@dataclass(frozen=True)
class HistoricalDatasetManifestCollection:
    """DTO imutavel para transportar manifests de datasets historicos."""

    collection_id: str
    collection_name: str
    manifests: tuple[HistoricalDatasetManifest, ...]
    total_manifests: int
    created_at: str
    collection_version: str

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
        if not isinstance(self.total_manifests, int):
            raise TypeError("total_manifests must be int")
        if self.total_manifests < 0:
            raise ValueError("total_manifests must be non-negative")
