"""Interface comum para adapters de dados historicos."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from market_data.historical_data_source import (
    HistoricalDataSource,
    HistoricalDataSourceResult,
)


class HistoricalDataAdapterBase(HistoricalDataSource):
    """Contrato publico para adapters historicos concretos."""

    supported_formats: tuple[str, ...] = ()
    adapter_label: str | None = None

    def supports(self, format_name: str) -> bool:
        """Indica se o adapter suporta um formato declarado."""

        normalized = self._normalize(format_name)
        return normalized in {self._normalize(item) for item in self.supported_formats}

    def can_handle(self, dataset_metadata: dict[str, Any]) -> bool:
        """Indica se o adapter pode lidar com metadados de dataset."""

        format_name = dataset_metadata.get("format") or dataset_metadata.get("provider")
        return isinstance(format_name, str) and self.supports(format_name)

    def get_metadata(self, dataset_ref: Any) -> dict[str, Any]:
        """Retorna metadados basicos sem abrir dataset fisico."""

        return {
            "adapter": self.adapter_name(),
            "dataset_ref": str(dataset_ref),
            "supported_formats": list(self.supported_formats),
        }

    def load_candles(self, dataset_ref: Any) -> HistoricalDataSourceResult:
        """Carrega candles pelo contrato legado do adapter."""

        return self.load(dataset_ref)

    def adapter_name(self) -> str:
        """Retorna identificacao publica do adapter."""

        return self.adapter_label or self.__class__.__name__

    @abstractmethod
    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega candles historicos por meio da porta abstrata."""

    def _normalize(self, value: str) -> str:
        return value.strip().lower()


HistoricalDataAdapter = HistoricalDataAdapterBase
