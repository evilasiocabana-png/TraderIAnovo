"""Contrato de metadados para datasets historicos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


REQUIRED_TEXT_FIELDS = (
    "symbol",
    "timeframe",
    "exchange",
    "timezone",
    "source",
    "format",
    "version",
    "first_timestamp",
    "last_timestamp",
)


@dataclass(frozen=True)
class HistoricalDatasetMetadata:
    """Metadados padronizados de um dataset historico."""

    symbol: str
    timeframe: str
    exchange: str
    timezone: str
    source: str
    format: str
    version: str
    first_timestamp: str
    last_timestamp: str
    candle_count: int
    checksum: str | None = None
    file_path: str | None = None
    dataset_id: str | None = None
    description: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.validate_required_fields()
        if not isinstance(self.candle_count, int):
            raise TypeError("candle_count must be int")
        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")
        if not isinstance(self.tags, tuple):
            object.__setattr__(self, "tags", tuple(self.tags))
        if any(not isinstance(tag, str) for tag in self.tags):
            raise TypeError("tags must contain only str values")

    def validate_required_fields(self) -> None:
        """Valida campos obrigatorios sem acessar dados fisicos."""

        for field_name in REQUIRED_TEXT_FIELDS:
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be str")
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Serializa metadados para dict simples."""

        data = asdict(self)
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoricalDatasetMetadata":
        """Reconstrui metadados a partir de dict."""

        payload = dict(data)
        tags = payload.get("tags", ())
        if isinstance(tags, list):
            payload["tags"] = tuple(tags)
        return cls(**payload)
