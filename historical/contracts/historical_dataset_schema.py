"""Contrato para schema logico de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetSchema:
    """DTO imutavel para descrever a estrutura logica de dataset historico."""

    schema_id: str
    schema_name: str
    schema_version: str
    columns: tuple[str, ...]
    primary_timestamp_column: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    created_at: str

    def __post_init__(self) -> None:
        for field_name in ("columns", "required_columns", "optional_columns"):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise TypeError(f"{field_name} must be a tuple[str, ...]")
            if any(not isinstance(column, str) for column in value):
                raise TypeError(f"{field_name} must contain only str values")
