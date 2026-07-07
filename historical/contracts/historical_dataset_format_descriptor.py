"""Contrato para descritor de formato de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetFormatDescriptor:
    """DTO imutavel para descrever um formato de dataset historico."""

    format_id: str
    format_name: str
    format_version: str
    file_extensions: tuple[str, ...]
    supports_compression: bool
    supports_schema_validation: bool
    supports_columnar_storage: bool
    supports_random_access: bool
    created_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.file_extensions, tuple):
            raise TypeError("file_extensions must be a tuple[str, ...]")
        if any(not isinstance(extension, str) for extension in self.file_extensions):
            raise TypeError("file_extensions must contain only str values")

        for field_name in (
            "supports_compression",
            "supports_schema_validation",
            "supports_columnar_storage",
            "supports_random_access",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
