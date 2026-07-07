"""Adapter DuckDB autorizado para dados historicos."""

from __future__ import annotations

from market_data.duckdb_historical_data_adapter import (
    DuckDBHistoricalDataAdapter as LegacyDuckDBHistoricalDataAdapter,
)


class DuckDBHistoricalDataAdapter(LegacyDuckDBHistoricalDataAdapter):
    """Contrato formal do adapter DuckDB historico."""

    supported_formats = ("duckdb",)
    adapter_label = "duckdb"
