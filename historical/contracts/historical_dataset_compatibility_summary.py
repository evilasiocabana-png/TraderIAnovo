"""Contrato para resumo de compatibilidade dataset-schema."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetCompatibilitySummary:
    """DTO imutavel para resumo executivo de compatibilidade historica."""

    dataset_id: str
    schema_id: str
    schema_version: str
    compatibility_level: str
    is_compatible: bool
    incompatible_column_count: int
    missing_column_count: int
    additional_column_count: int
    analyzed_at: str
    analyzer_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.is_compatible, bool):
            raise TypeError("is_compatible must be bool")
        for field_name in (
            "incompatible_column_count",
            "missing_column_count",
            "additional_column_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
