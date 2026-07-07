"""Contrato para versao de schema de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetSchemaVersion:
    """DTO imutavel para representar uma versao de schema historico."""

    schema_id: str
    schema_version: str
    version_description: str
    effective_from: str
    effective_until: str | None
    is_current: bool
    is_backward_compatible: bool
    created_at: str

    def __post_init__(self) -> None:
        if self.effective_until is not None and not isinstance(self.effective_until, str):
            raise TypeError("effective_until must be str or None")
        for field_name in ("is_current", "is_backward_compatible"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
