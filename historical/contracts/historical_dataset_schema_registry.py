"""Contrato para registry logico de schemas historicos."""

from dataclasses import dataclass

from historical.contracts.historical_dataset_schema import HistoricalDatasetSchema


@dataclass(frozen=True)
class HistoricalDatasetSchemaRegistry:
    """DTO imutavel para agrupar schemas historicos."""

    registry_id: str
    registry_name: str
    schemas: tuple[HistoricalDatasetSchema, ...]
    total_schemas: int
    registry_version: str
    generated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.schemas, tuple):
            raise TypeError("schemas must be a tuple[HistoricalDatasetSchema, ...]")
        if any(not isinstance(schema, HistoricalDatasetSchema) for schema in self.schemas):
            raise TypeError("schemas must contain only HistoricalDatasetSchema values")
        if not isinstance(self.total_schemas, int):
            raise TypeError("total_schemas must be int")
        if self.total_schemas < 0:
            raise ValueError("total_schemas must be non-negative")
