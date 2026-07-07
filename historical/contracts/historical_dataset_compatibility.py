"""Contrato para compatibilidade entre dataset historico e schema."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetCompatibility:
    """DTO imutavel para resultado de compatibilidade estrutural historica."""

    dataset_id: str
    schema_id: str
    schema_version: str
    is_compatible: bool
    compatibility_level: str
    incompatible_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    additional_columns: tuple[str, ...]
    compatibility_notes: tuple[str, ...]
    analyzed_at: str
    analyzer_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.is_compatible, bool):
            raise TypeError("is_compatible must be bool")
        for field_name in (
            "incompatible_columns",
            "missing_columns",
            "additional_columns",
            "compatibility_notes",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise TypeError(f"{field_name} must be a tuple[str, ...]")
            if any(not isinstance(item, str) for item in value):
                raise TypeError(f"{field_name} must contain only str values")
