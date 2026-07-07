"""Contrato para relatorio consolidado de fingerprints historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)


@dataclass(frozen=True)
class HistoricalDatasetFingerprintReport:
    """DTO imutavel para relatorio de fingerprints de datasets historicos."""

    report_id: str
    report_name: str
    fingerprints: tuple[HistoricalDatasetFingerprint, ...]
    total_datasets: int
    generated_at: str
    generator_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.fingerprints, tuple):
            raise TypeError(
                "fingerprints must be a tuple[HistoricalDatasetFingerprint, ...]"
            )
        if any(
            not isinstance(fingerprint, HistoricalDatasetFingerprint)
            for fingerprint in self.fingerprints
        ):
            raise TypeError(
                "fingerprints must contain only HistoricalDatasetFingerprint values"
            )
        if not isinstance(self.total_datasets, int):
            raise TypeError("total_datasets must be int")
        if self.total_datasets < 0:
            raise ValueError("total_datasets must be non-negative")
