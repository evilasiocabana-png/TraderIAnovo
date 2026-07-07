"""Contrato para colecao de bundles historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_bundle import HistoricalDatasetBundle


@dataclass(frozen=True)
class HistoricalDatasetBundleCollection:
    """DTO imutavel para transportar bundles logicos de datasets historicos."""

    collection_id: str
    collection_name: str
    bundles: tuple[HistoricalDatasetBundle, ...]
    total_bundles: int
    created_at: str
    collection_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.bundles, tuple):
            raise TypeError(
                "bundles must be a tuple[HistoricalDatasetBundle, ...]"
            )
        if any(
            not isinstance(bundle, HistoricalDatasetBundle) for bundle in self.bundles
        ):
            raise TypeError(
                "bundles must contain only HistoricalDatasetBundle values"
            )
        if not isinstance(self.total_bundles, int):
            raise TypeError("total_bundles must be int")
        if self.total_bundles < 0:
            raise ValueError("total_bundles must be non-negative")
