"""Contrato para resumo executivo de qualidade de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetValidationSummary:
    """DTO imutavel para resumo de qualidade de dataset historico."""

    dataset_id: str
    overall_status: str
    quality_score: float
    records_checked: int
    invalid_records: int
    gap_count: int
    duplicate_timestamp_count: int
    critical_error_count: int
    warning_count: int
    validated_at: str
    validator_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.quality_score, (int, float)):
            raise TypeError("quality_score must be numeric")
        for field_name in (
            "records_checked",
            "invalid_records",
            "gap_count",
            "duplicate_timestamp_count",
            "critical_error_count",
            "warning_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
