"""Contrato para descritor de origem logica de datasets historicos."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetSourceDescriptor:
    """DTO imutavel para descrever uma origem logica de dados historicos."""

    source_id: str
    source_name: str
    source_description: str
    provider_id: str
    supported_symbols: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    supported_formats: tuple[str, ...]
    is_read_only: bool
    is_available: bool
    created_at: str
    source_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "supported_symbols",
            "supported_timeframes",
            "supported_formats",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise TypeError(f"{field_name} must be a tuple[str, ...]")
            if any(not isinstance(item, str) for item in value):
                raise TypeError(f"{field_name} must contain only str values")

        for field_name in ("is_read_only", "is_available"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
