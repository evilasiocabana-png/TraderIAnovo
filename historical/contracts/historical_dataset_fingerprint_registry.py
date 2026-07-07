"""Contrato para registry logico de fingerprints historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)


@dataclass(frozen=True)
class HistoricalDatasetFingerprintRegistry:
    """DTO imutavel para agrupar fingerprints historicos conhecidos."""

    registry_id: str
    registry_name: str
    fingerprints: tuple[HistoricalDatasetFingerprint, ...]
    total_fingerprints: int
    registry_version: str
    generated_at: str

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
        if not isinstance(self.total_fingerprints, int):
            raise TypeError("total_fingerprints must be int")
        if self.total_fingerprints < 0:
            raise ValueError("total_fingerprints must be non-negative")
