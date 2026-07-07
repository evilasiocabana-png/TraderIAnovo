"""Contrato oficial da interface DataProvider."""

from __future__ import annotations

import unittest
from pathlib import Path

from market_data import DataProvider, HistoricalDataProvider, MarketDataProvider
from market_data.adapters.csv_historical_data_adapter import CsvHistoricalDataAdapter
from market_data.adapters.parquet_historical_data_adapter import (
    ParquetHistoricalDataAdapter,
)


class DataProviderInterfaceTest(unittest.TestCase):
    """Protege a porta oficial de leitura de dados historicos."""

    def test_historical_provider_implementa_data_provider(self) -> None:
        provider = HistoricalDataProvider()

        self.assertIsInstance(provider, DataProvider)
        self.assertTrue(issubclass(HistoricalDataProvider, DataProvider))

    def test_market_data_provider_permanece_alias_compativel(self) -> None:
        self.assertIs(MarketDataProvider, DataProvider)
        self.assertTrue(issubclass(HistoricalDataProvider, MarketDataProvider))

    def test_provider_resolve_suporte_csv_e_parquet(self) -> None:
        provider = HistoricalDataProvider()

        csv_adapter = provider.resolve_adapter("csv")
        parquet_adapter = provider.resolve_adapter("parquet")

        self.assertIsInstance(csv_adapter, CsvHistoricalDataAdapter)
        self.assertIsInstance(parquet_adapter, ParquetHistoricalDataAdapter)

    def test_provider_carrega_csv_por_interface_oficial(self) -> None:
        provider: DataProvider = HistoricalDataProvider()

        dataset = provider.load(
            Path("tests/fixtures/historical_data/wdo_1m_sample.csv"),
            symbol="WDO",
            timeframe="1m",
        )

        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.total_candles, 2)

    def test_interface_nao_cria_dependencia_operacional(self) -> None:
        source = Path("market_data/data_provider.py").read_text(encoding="utf-8")
        forbidden_terms = (
            "dashboard",
            "replay",
            "research",
            "broker",
            "MetaTrader5",
            "send_order",
            "order_send",
        )

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
