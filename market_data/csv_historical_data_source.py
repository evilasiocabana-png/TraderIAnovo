"""Adaptador CSV para a porta de dados historicos."""

from dataclasses import dataclass
from typing import Any

from data.historical_data_loader import HistoricalDataLoader
from market_data.adapters import HistoricalDataAdapter
from market_data.historical_data_source import (
    HistoricalDataSourceResult,
)


@dataclass
class CsvHistoricalDataSource(HistoricalDataAdapter):
    """Le candles historicos usando o importador CSV legado."""

    supported_formats = ("csv",)
    adapter_label = "csv"
    loader_factory: type[HistoricalDataLoader] = HistoricalDataLoader

    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega uma origem CSV e retorna candles ou erros normalizados."""
        loader = self.loader_factory().load_csv(source)
        load_errors = list(loader.errors)
        if load_errors or not loader.validate():
            return HistoricalDataSourceResult(
                candles=[],
                errors=load_errors or list(loader.errors),
            )
        return HistoricalDataSourceResult(
            candles=loader.candles(),
            errors=[],
        )
