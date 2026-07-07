"""Contrato para coluna logica de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetColumn:
    """DTO imutavel para descrever uma coluna logica de dataset historico."""

    column_name: str
    logical_type: str
    physical_type: str
    nullable: bool
    required: bool
    description: str
    default_value: str | None
    metadata_version: str

    def __post_init__(self) -> None:
        for field_name in ("nullable", "required"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
        if self.default_value is not None and not isinstance(self.default_value, str):
            raise TypeError("default_value must be str or None")
