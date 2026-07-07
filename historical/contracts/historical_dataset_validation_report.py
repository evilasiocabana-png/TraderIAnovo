"""Contrato para relatorio consolidado de validacoes historicas."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_validation import (
    HistoricalDatasetValidationResult,
)


@dataclass(frozen=True)
class HistoricalDatasetValidationReport:
    """DTO imutavel para relatorio consolidado de validacoes historicas."""

    report_id: str
    datasets_validated: int
    total_records_checked: int
    total_invalid_records: int
    total_gaps: int
    total_duplicate_timestamps: int
    total_critical_errors: int
    total_warnings: int
    validation_results: tuple[HistoricalDatasetValidationResult, ...]
    generated_at: str
    validator_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.validation_results, tuple):
            raise TypeError(
                "validation_results must be a tuple[HistoricalDatasetValidationResult, ...]"
            )
        if any(
            not isinstance(result, HistoricalDatasetValidationResult)
            for result in self.validation_results
        ):
            raise TypeError(
                "validation_results must contain only HistoricalDatasetValidationResult values"
            )
        for field_name in (
            "datasets_validated",
            "total_records_checked",
            "total_invalid_records",
            "total_gaps",
            "total_duplicate_timestamps",
            "total_critical_errors",
            "total_warnings",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
