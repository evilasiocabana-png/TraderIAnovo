"""Contrato para descritor composto de dataset historico."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_compatibility_summary import (
    HistoricalDatasetCompatibilitySummary,
)
from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)
from historical.contracts.historical_dataset_identity import HistoricalDatasetIdentity
from historical.contracts.historical_dataset_metadata import HistoricalDatasetMetadata
from historical.contracts.historical_dataset_reference import HistoricalDatasetReference
from historical.contracts.historical_dataset_validation_summary import (
    HistoricalDatasetValidationSummary,
)


@dataclass(frozen=True)
class HistoricalDatasetDescriptor:
    """DTO imutavel para compor a descricao completa de dataset historico."""

    identity: HistoricalDatasetIdentity
    reference: HistoricalDatasetReference
    metadata: HistoricalDatasetMetadata
    validation_summary: HistoricalDatasetValidationSummary
    compatibility_summary: HistoricalDatasetCompatibilitySummary
    fingerprint: HistoricalDatasetFingerprint
    descriptor_version: str
    created_at: str

    def __post_init__(self) -> None:
        expected_types = {
            "identity": HistoricalDatasetIdentity,
            "reference": HistoricalDatasetReference,
            "metadata": HistoricalDatasetMetadata,
            "validation_summary": HistoricalDatasetValidationSummary,
            "compatibility_summary": HistoricalDatasetCompatibilitySummary,
            "fingerprint": HistoricalDatasetFingerprint,
        }
        for field_name, expected_type in expected_types.items():
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be {expected_type.__name__}")
