"""Adapter Parquet autorizado para dados historicos."""

from __future__ import annotations

from market_data.parquet_historical_data_adapter import (
    ParquetHistoricalDataAdapter as LegacyParquetHistoricalDataAdapter,
)


class ParquetHistoricalDataAdapter(LegacyParquetHistoricalDataAdapter):
    """Contrato formal do adapter Parquet historico."""

    supported_formats = ("parquet",)
    adapter_label = "parquet"
