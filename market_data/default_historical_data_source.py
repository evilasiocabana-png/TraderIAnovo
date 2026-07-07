"""Composicao padrao da fonte historica atual."""

from market_data.adapters import HistoricalDataAdapter
from market_data.historical_data_source import HistoricalDataSource
from market_data.historical_data_source_registry import create_historical_data_source


def create_default_historical_data_source() -> HistoricalDataAdapter:
    """Cria a fonte historica padrao atual."""
    return create_historical_data_source("csv")
