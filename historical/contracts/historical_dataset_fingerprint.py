"""Contrato para fingerprint estrutural de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetFingerprint:
    """DTO imutavel para identidade estrutural de dataset historico."""

    dataset_id: str
    schema_id: str
    schema_version: str
    fingerprint_algorithm: str
    fingerprint_value: str
    generated_at: str
    generator_version: str
