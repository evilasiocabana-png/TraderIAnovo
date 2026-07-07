"""Provider oficial para dados historicos do TraderIA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from market_data.catalog import (
    HistoricalDatasetCatalog as StructuralHistoricalDatasetCatalog,
    HistoricalDatasetRecord,
)
from market_data.adapters import HistoricalDataAdapter
from market_data.adapters.historical_adapter_registry import (
    HistoricalAdapterRegistry,
    create_default_historical_adapter_registry,
)
from market_data.default_historical_data_source import (
    create_default_historical_data_source,
)
from market_data.historical_data_source import HistoricalDataSource
from market_data.historical_dataset import HistoricalDataset
from market_data.data_provider import DataProvider


@dataclass
class HistoricalDataProvider(DataProvider):
    """Fornece datasets historicos usando uma fonte historica abstrata."""

    data_source: HistoricalDataSource = field(
        default_factory=create_default_historical_data_source
    )
    dataset_catalog: StructuralHistoricalDatasetCatalog = field(
        default_factory=StructuralHistoricalDatasetCatalog
    )
    adapter_registry: HistoricalAdapterRegistry = field(
        default_factory=create_default_historical_adapter_registry
    )
    loaded_datasets: list[HistoricalDataset] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def load(
        self,
        source: Any,
        symbol: str = "WDO",
        timeframe: str = "UNKNOWN",
    ) -> HistoricalDataset:
        """Carrega uma origem historica e retorna HistoricalDataset."""
        self.errors.clear()
        result = self.data_source.load(source)
        if result.errors or result.is_empty:
            self.errors.extend(result.errors)
            return self._empty_dataset(symbol, timeframe)
        dataset = self._dataset(symbol, timeframe, result.candles)
        self.loaded_datasets.append(dataset)
        return dataset

    def load_dataset(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> HistoricalDataset:
        """Carrega dataset catalogado pela estrutura historica oficial."""
        self.errors.clear()
        metadata = self.get_metadata(symbol, timeframe, period)
        if metadata is None:
            self.errors.append("Dataset historico nao catalogado.")
            return self._empty_dataset(symbol, timeframe)

        source = self._dataset_source(symbol, timeframe, period, metadata)
        if source is None:
            self.errors.append("Dataset historico sem arquivo de dados.")
            return self._empty_dataset(symbol, timeframe)

        try:
            adapter = self.resolve_adapter(str(metadata.get("format") or "csv"))
        except KeyError as exc:
            self.errors.append(str(exc))
            return self._empty_dataset(symbol, timeframe)

        result = adapter.load(source)
        if result.errors or result.is_empty:
            self.errors.extend(result.errors)
            return self._empty_dataset(symbol, timeframe)

        dataset = self._dataset(symbol, timeframe, result.candles)
        self.loaded_datasets.append(dataset)
        return dataset

    def symbols(self) -> list[str]:
        """Lista simbolos carregados pelo provider."""
        symbols = {dataset.symbol for dataset in self.loaded_datasets}
        if not symbols:
            return ["WDO"]
        return sorted(symbols)

    def available_periods(self) -> list[str]:
        """Lista timeframes carregados pelo provider."""
        periods = {dataset.timeframe for dataset in self.loaded_datasets}
        if not periods:
            return []
        return sorted(periods)

    def list_datasets(self) -> list[HistoricalDatasetRecord]:
        """Lista datasets catalogados sem carregar candles."""
        return self.dataset_catalog.list_datasets()

    def list_symbols(self) -> list[str]:
        """Lista ativos catalogados pela estrutura historica."""
        return self.dataset_catalog.list_symbols()

    def list_timeframes(self, symbol: str) -> list[str]:
        """Lista timeframes catalogados para um ativo."""
        return self.dataset_catalog.list_timeframes(symbol)

    def dataset_exists(self, symbol: str, timeframe: str, period: str) -> bool:
        """Verifica se um dataset catalogado existe."""
        return self.dataset_catalog.dataset_exists(symbol, timeframe, period)

    def get_metadata(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> dict[str, Any] | None:
        """Retorna metadados declarativos de um dataset catalogado."""
        return self.dataset_catalog.get_dataset_metadata(symbol, timeframe, period)

    def get_dataset(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> dict[str, Any] | None:
        """Retorna a descricao publica do dataset sem leitura fisica."""
        return self.get_metadata(symbol, timeframe, period)

    def resolve_adapter(self, name: str) -> HistoricalDataAdapter:
        """Resolve adapter historico pela porta abstrata registrada."""
        return self.adapter_registry.get_adapter_for_format(name)

    def _dataset_source(
        self,
        symbol: str,
        timeframe: str,
        period: str,
        metadata: dict[str, Any],
    ) -> str | None:
        file_name = metadata.get("file_path") or metadata.get("data_file")
        if not isinstance(file_name, str) or not file_name.strip():
            return None
        record = self._catalog_record(symbol, timeframe, period)
        if record is None:
            return None
        return f"{record.path}/{file_name}"

    def _catalog_record(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> HistoricalDatasetRecord | None:
        for record in self.list_datasets():
            if (
                record.symbol == symbol
                and record.timeframe == timeframe
                and record.period == period
            ):
                return record
        return None

    def _dataset(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any],
    ) -> HistoricalDataset:
        return HistoricalDataset(
            symbol=symbol,
            timeframe=timeframe,
            start_date=self._start_date(candles),
            end_date=self._end_date(candles),
            candles=list(candles),
        )

    def _empty_dataset(self, symbol: str, timeframe: str) -> HistoricalDataset:
        return HistoricalDataset(
            symbol=symbol,
            timeframe=timeframe,
            start_date=None,
            end_date=None,
            candles=[],
        )

    def _start_date(self, candles: list[Any]) -> str | None:
        if not candles:
            return None
        return candles[0].data

    def _end_date(self, candles: list[Any]) -> str | None:
        if not candles:
            return None
        return candles[-1].data
