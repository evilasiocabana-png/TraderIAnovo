"""Registry oficial de adapters historicos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from market_data.adapters.historical_data_adapter import HistoricalDataAdapter


@dataclass
class HistoricalAdapterRegistry:
    """Registro de adapters historicos por contrato abstrato."""

    adapters: dict[str, HistoricalDataAdapter] = field(default_factory=dict)

    def register(self, adapter: HistoricalDataAdapter) -> None:
        """Registra um adapter e valida duplicidade de nome/formato."""

        name = self._normalize(adapter.adapter_name())
        if name in self.adapters:
            raise ValueError(f"Adapter historico duplicado: {adapter.adapter_name()}")
        duplicate_formats = [
            format_name
            for format_name in adapter.supported_formats
            if self.has_adapter(format_name)
        ]
        if duplicate_formats:
            raise ValueError(
                "Formato historico ja registrado: " + ", ".join(duplicate_formats)
            )
        self.adapters[name] = adapter

    def unregister(self, adapter_name: str) -> None:
        """Remove adapter registrado pelo nome."""

        normalized = self._normalize(adapter_name)
        if normalized not in self.adapters:
            raise KeyError(f"Adapter historico nao registrado: {adapter_name}")
        del self.adapters[normalized]

    def list_adapters(self) -> list[str]:
        """Lista nomes dos adapters registrados."""

        return sorted(self.adapters)

    def get_adapter_for_format(self, format_name: str) -> HistoricalDataAdapter:
        """Retorna adapter que suporta o formato informado."""

        for adapter in self.adapters.values():
            if adapter.supports(format_name):
                return adapter
        raise KeyError(f"Nenhum adapter historico suporta o formato: {format_name}")

    def get_adapter_for_dataset(
        self,
        dataset_metadata: dict[str, Any],
    ) -> HistoricalDataAdapter:
        """Retorna adapter capaz de lidar com metadados de dataset."""

        for adapter in self.adapters.values():
            if adapter.can_handle(dataset_metadata):
                return adapter
        format_name = dataset_metadata.get("format") or dataset_metadata.get("provider")
        raise KeyError(f"Nenhum adapter historico suporta o dataset: {format_name}")

    def has_adapter(self, format_name: str) -> bool:
        """Indica se algum adapter suporta o formato."""

        return any(adapter.supports(format_name) for adapter in self.adapters.values())

    def _normalize(self, value: str) -> str:
        return value.strip().lower()


def create_default_historical_adapter_registry() -> HistoricalAdapterRegistry:
    """Cria registry padrao com adapters historicos conhecidos."""

    from market_data.adapters.csv_historical_data_adapter import (
        CsvHistoricalDataAdapter,
    )
    from market_data.adapters.duckdb_historical_data_adapter import (
        DuckDBHistoricalDataAdapter,
    )
    from market_data.adapters.parquet_historical_data_adapter import (
        ParquetHistoricalDataAdapter,
    )

    registry = HistoricalAdapterRegistry()
    registry.register(CsvHistoricalDataAdapter())
    registry.register(ParquetHistoricalDataAdapter())
    registry.register(DuckDBHistoricalDataAdapter())
    return registry
