"""Contrato para manifest logico de dataset historico."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_compatibility_summary import (
    HistoricalDatasetCompatibilitySummary,
)
from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)
from historical.contracts.historical_dataset_identity import HistoricalDatasetIdentity
from historical.contracts.historical_dataset_metadata import HistoricalDatasetMetadata
from historical.contracts.historical_dataset_schema_version import (
    HistoricalDatasetSchemaVersion,
)
from historical.contracts.historical_dataset_validation_summary import (
    HistoricalDatasetValidationSummary,
)


@dataclass(frozen=True)
class HistoricalDatasetManifest:
    """DTO imutavel para manifest logico de dataset historico."""

    identity: HistoricalDatasetIdentity
    metadata: HistoricalDatasetMetadata
    schema_version: HistoricalDatasetSchemaVersion
    fingerprint: HistoricalDatasetFingerprint
    validation_summary: HistoricalDatasetValidationSummary
    compatibility_summary: HistoricalDatasetCompatibilitySummary
    manifest_version: str
    generated_at: str

    def __post_init__(self) -> None:
        expected_types = {
            "identity": HistoricalDatasetIdentity,
            "metadata": HistoricalDatasetMetadata,
            "schema_version": HistoricalDatasetSchemaVersion,
            "fingerprint": HistoricalDatasetFingerprint,
            "validation_summary": HistoricalDatasetValidationSummary,
            "compatibility_summary": HistoricalDatasetCompatibilitySummary,
        }
        for field_name, expected_type in expected_types.items():
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be {expected_type.__name__}")
