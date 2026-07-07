"""Contrato para registry logico de bundles historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_bundle import HistoricalDatasetBundle


@dataclass(frozen=True)
class HistoricalDatasetBundleRegistry:
    """DTO imutavel para registrar bundles historicos conhecidos."""

    registry_id: str
    registry_name: str
    bundles: tuple[HistoricalDatasetBundle, ...]
    total_bundles: int
    registry_version: str
    generated_at: str

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
