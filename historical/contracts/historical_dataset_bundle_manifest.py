"""Contrato para manifest logico de bundle historico."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_package import HistoricalDatasetPackage


@dataclass(frozen=True)
class HistoricalDatasetBundleManifest:
    """DTO imutavel para intercambio logico de bundles historicos."""

    bundle_id: str
    bundle_name: str
    bundle_version: str
    packages: tuple[HistoricalDatasetPackage, ...]
    total_packages: int
    total_datasets: int
    manifest_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.packages, tuple):
            raise TypeError(
                "packages must be a tuple[HistoricalDatasetPackage, ...]"
            )
        if any(
            not isinstance(package, HistoricalDatasetPackage)
            for package in self.packages
        ):
            raise TypeError(
                "packages must contain only HistoricalDatasetPackage values"
            )
        if not isinstance(self.total_packages, int):
            raise TypeError("total_packages must be int")
        if not isinstance(self.total_datasets, int):
            raise TypeError("total_datasets must be int")
        if self.total_packages < 0:
            raise ValueError("total_packages must be non-negative")
        if self.total_datasets < 0:
            raise ValueError("total_datasets must be non-negative")
