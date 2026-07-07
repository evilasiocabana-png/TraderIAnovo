"""Camada oficial de Market Data do TraderIA."""

from market_data.csv_historical_data_source import CsvHistoricalDataSource
from market_data.duckdb_historical_data_adapter import DuckDBHistoricalDataAdapter
from market_data.data_provider import DataProvider
from market_data.historical_data_source import (
    HistoricalDataSource,
    HistoricalDataSourceResult,
)
from market_data.historical_data_provider import HistoricalDataProvider
from market_data.historical_importer import (
    HistoricalImporter,
    HistoricalImportResult,
)
from market_data.historical_data_source_registry import (
    HistoricalDataSourceRegistry,
    create_default_historical_data_source_registry,
    create_historical_data_source,
)
from market_data.historical_dataset_catalog import (
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
)
from market_data.historical_dataset import HistoricalDataset
from market_data.historical_dataset_quality_repository import (
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
)
from market_data.json_historical_dataset_quality_repository import (
    JsonHistoricalDatasetQualityRepository,
    create_default_historical_dataset_quality_repository,
)
from market_data.market_data_provider import MarketDataProvider
from market_data.parquet_historical_data_adapter import (
    ParquetHistoricalDataAdapter,
)

__all__ = [
    "CsvHistoricalDataSource",
    "DataProvider",
    "DuckDBHistoricalDataAdapter",
    "HistoricalDataSource",
    "HistoricalDataSourceResult",
    "HistoricalDataProvider",
    "HistoricalImporter",
    "HistoricalImportResult",
    "HistoricalDataSourceRegistry",
    "HistoricalDatasetCatalog",
    "HistoricalDatasetMetadata",
    "HistoricalDataset",
    "HistoricalDatasetQualityRepository",
    "HistoricalDatasetQualityStatus",
    "HistoricalDatasetQualityValidationRecord",
    "JsonHistoricalDatasetQualityRepository",
    "MarketDataProvider",
    "ParquetHistoricalDataAdapter",
    "create_default_historical_data_source_registry",
    "create_historical_data_source",
    "create_default_historical_dataset_quality_repository",
]
