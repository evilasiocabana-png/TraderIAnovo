"""Contrato para descritor de provider de datasets historicos."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetProviderDescriptor:
    """DTO imutavel para descrever um provider historico disponivel."""

    provider_id: str
    provider_name: str
    provider_version: str
    provider_description: str
    supported_symbols: tuple[str, ...]
    supported_timeframes: tuple[str, ...]
    supported_formats: tuple[str, ...]
    supports_streaming: bool
    supports_incremental_loading: bool
    supports_validation: bool
    created_at: str

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

        for field_name in (
            "supports_streaming",
            "supports_incremental_loading",
            "supports_validation",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
