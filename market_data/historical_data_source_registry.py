"""Registry simples para fontes historicas."""

from collections.abc import Callable
from dataclasses import dataclass, field

from market_data.adapters import HistoricalDataAdapter
from market_data.csv_historical_data_source import CsvHistoricalDataSource
from market_data.duckdb_historical_data_adapter import DuckDBHistoricalDataAdapter
from market_data.historical_data_source import HistoricalDataSource
from market_data.parquet_historical_data_adapter import (
    ParquetHistoricalDataAdapter,
)


HistoricalDataSourceFactory = Callable[[], HistoricalDataAdapter]


@dataclass
class HistoricalDataSourceRegistry:
    """Registro de adaptadores de fontes historicas por nome."""

    factories: dict[str, HistoricalDataSourceFactory] = field(default_factory=dict)

    def register(
        self,
        name: str,
        factory: HistoricalDataSourceFactory,
    ) -> None:
        """Registra uma fabrica de fonte historica."""
        self.factories[self._normalize(name)] = factory

    def create(self, name: str = "csv") -> HistoricalDataAdapter:
        """Cria uma fonte historica registrada."""
        normalized = self._normalize(name)
        if normalized not in self.factories:
            raise KeyError(f"Fonte historica nao registrada: {name}")
        return self.factories[normalized]()

    def names(self) -> list[str]:
        """Lista fontes historicas registradas."""
        return sorted(self.factories)

    def _normalize(self, name: str) -> str:
        return name.strip().lower()


def create_default_historical_data_source_registry() -> HistoricalDataSourceRegistry:
    """Cria o registry padrao mantendo CSV como fonte default."""
    registry = HistoricalDataSourceRegistry()
    registry.register("csv", CsvHistoricalDataSource)
    registry.register("parquet", ParquetHistoricalDataAdapter)
    registry.register("duckdb", DuckDBHistoricalDataAdapter)
    return registry


def create_historical_data_source(name: str = "csv") -> HistoricalDataSource:
    """Cria uma fonte historica a partir do registry padrao."""
    return create_default_historical_data_source_registry().create(name)
