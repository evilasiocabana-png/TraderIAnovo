"""Contrato para relatorio consolidado de compatibilidade historica."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_compatibility import (
    HistoricalDatasetCompatibility,
)


@dataclass(frozen=True)
class HistoricalDatasetCompatibilityReport:
    """DTO imutavel para relatorio de compatibilidade dataset-schema."""

    report_id: str
    report_name: str
    compatibility_results: tuple[HistoricalDatasetCompatibility, ...]
    total_datasets_analyzed: int
    compatible_datasets: int
    incompatible_datasets: int
    generated_at: str
    analyzer_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.compatibility_results, tuple):
            raise TypeError(
                "compatibility_results must be a tuple[HistoricalDatasetCompatibility, ...]"
            )
        if any(
            not isinstance(result, HistoricalDatasetCompatibility)
            for result in self.compatibility_results
        ):
            raise TypeError(
                "compatibility_results must contain only HistoricalDatasetCompatibility values"
            )
        for field_name in (
            "total_datasets_analyzed",
            "compatible_datasets",
            "incompatible_datasets",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
