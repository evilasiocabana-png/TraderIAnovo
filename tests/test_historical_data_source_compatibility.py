"""Testes de compatibilidade entre fontes historicas CSV, Parquet e DuckDB."""

import ast
import tempfile
from pathlib import Path
import unittest

import duckdb
import pandas as pd

from domain.candle import Candle
from market_data import (
    CsvHistoricalDataSource,
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    HistoricalDataset,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    ParquetHistoricalDataAdapter,
    create_historical_data_source,
)


class HistoricalDataSourceCompatibilityTest(unittest.TestCase):
    """Compara contratos expostos por adapters historicos."""

    def test_csv_parquet_e_duckdb_retornam_historical_dataset_equivalente(
        self,
    ) -> None:
        datasets = {
            "csv": self._dataset("csv", self._csv_source()),
            "parquet": self._dataset("parquet", self._parquet_source()),
            "duckdb": self._dataset("duckdb", self._duckdb_source()),
        }

        for provider_name, dataset in datasets.items():
            with self.subTest(provider=provider_name):
                self.assertIsInstance(dataset, HistoricalDataset)
                self.assertEqual(dataset.symbol, "WDO")
                self.assertEqual(dataset.timeframe, "1m")
                self.assertEqual(dataset.start_date, "2026-06-26 09:00")
                self.assertEqual(dataset.end_date, "2026-06-26 09:02")
                self.assertEqual(dataset.total_candles, 3)
                self.assertIsInstance(dataset.candles, list)
                self.assertTrue(
                    all(isinstance(candle, Candle) for candle in dataset.candles)
                )

        self.assertEqual(
            self._candle_snapshot(datasets["csv"]),
            self._candle_snapshot(datasets["parquet"]),
        )
        self.assertEqual(
            self._candle_snapshot(datasets["csv"]),
            self._candle_snapshot(datasets["duckdb"]),
        )

    def test_catalogo_preserva_metadados_obrigatorios_por_provider(self) -> None:
        catalog = HistoricalDatasetCatalog()
        csv_metadata = self._metadata("wdo_csv_1m", "csv")
        parquet_metadata = self._metadata("wdo_parquet_1m", "parquet")
        duckdb_metadata = self._metadata("wdo_duckdb_1m", "duckdb")

        catalog.register_dataset(csv_metadata, source=self._csv_source())
        catalog.register_dataset(parquet_metadata, source=self._parquet_source())
        catalog.register_dataset(duckdb_metadata, source=self._duckdb_source())

        for metadata in catalog.list_datasets():
            with self.subTest(dataset_id=metadata.dataset_id):
                self.assertIsInstance(metadata.dataset_id, str)
                self.assertEqual(metadata.ativo, "WDO")
                self.assertEqual(metadata.timeframe, "1m")
                self.assertEqual(metadata.start_date, "2026-06-26 09:00")
                self.assertEqual(metadata.end_date, "2026-06-26 09:02")
                self.assertEqual(metadata.estimated_candles, 3)
                self.assertIn(metadata.provider, {"csv", "parquet", "duckdb"})
                self.assertFalse(hasattr(metadata, "candles"))

    def test_contrato_completo_de_dataset_e_metadados_por_provider(self) -> None:
        sources = {
            "csv": self._csv_source(),
            "parquet": self._parquet_source(),
            "duckdb": self._duckdb_source(),
        }

        for provider_name, source in sources.items():
            with self.subTest(provider=provider_name):
                metadata = self._metadata(
                    f"wdo_{provider_name}_1m",
                    provider_name,
                )
                dataset = self._dataset(provider_name, source)

                self.assertEqual(metadata.dataset_id, f"wdo_{provider_name}_1m")
                self.assertEqual(metadata.provider, provider_name)
                self.assertEqual(metadata.ativo, "WDO")
                self.assertEqual(metadata.timeframe, dataset.timeframe)
                self.assertEqual(metadata.start_date, dataset.start_date)
                self.assertEqual(metadata.end_date, dataset.end_date)
                self.assertEqual(metadata.estimated_candles, dataset.total_candles)
                self.assertIsInstance(dataset, HistoricalDataset)
                self.assertIsInstance(dataset.candles, list)
                self.assertTrue(
                    all(isinstance(candle, Candle) for candle in dataset.candles)
                )

    def test_csv_continua_default_e_parquet_duckdb_podem_ser_selecionados(
        self,
    ) -> None:
        default_source = create_historical_data_source()
        parquet_source = create_historical_data_source("parquet")
        duckdb_source = create_historical_data_source("duckdb")
        csv_source = create_historical_data_source("csv")

        self.assertIsInstance(default_source, CsvHistoricalDataSource)
        self.assertIsInstance(csv_source, CsvHistoricalDataSource)
        self.assertIsInstance(parquet_source, ParquetHistoricalDataAdapter)
        self.assertIsInstance(duckdb_source, DuckDBHistoricalDataAdapter)

    def test_troca_de_provider_nao_afeta_camadas_superiores(self) -> None:
        forbidden_terms = (
            "parquet_historical_data_adapter",
            "duckdb_historical_data_adapter",
            "csv_historical_data_source",
            "read_parquet",
            "duckdb",
            "load_csv",
        )
        for path in self._upper_layer_files():
            source = path.read_text(encoding="utf-8")
            imports = self._imports(path)
            with self.subTest(path=str(path)):
                for term in forbidden_terms:
                    self.assertNotIn(term, source)
                self.assertNotIn("market_data.parquet_historical_data_adapter", imports)
                self.assertNotIn("market_data.duckdb_historical_data_adapter", imports)
                self.assertNotIn("market_data.csv_historical_data_source", imports)

    def _dataset(self, provider_name: str, source: Path) -> HistoricalDataset:
        return HistoricalDataProvider(
            data_source=create_historical_data_source(provider_name),
        ).load(source, symbol="WDO", timeframe="1m")

    def _metadata(self, dataset_id: str, provider: str) -> HistoricalDatasetMetadata:
        return HistoricalDatasetMetadata(
            dataset_id=dataset_id,
            ativo="WDO",
            timeframe="1m",
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:02",
            estimated_candles=3,
            provider=provider,
        )

    def _candle_snapshot(
        self,
        dataset: HistoricalDataset,
    ) -> list[tuple[str, float, float, float, float, int]]:
        return [
            (
                candle.data,
                candle.abertura,
                candle.maxima,
                candle.minima,
                candle.fechamento,
                candle.volume,
            )
            for candle in dataset.candles
        ]

    def _rows(self) -> list[dict[str, object]]:
        rows = []
        for index in range(3):
            close = 100.0 + index
            rows.append(
                {
                    "datetime": f"2026-06-26 09:{index:02d}",
                    "open": close - 1,
                    "high": close + 2,
                    "low": close - 2,
                    "close": close,
                    "volume": 1000,
                }
            )
        return rows

    def _csv_source(self) -> Path:
        lines = ["datetime,open,high,low,close,volume"]
        for row in self._rows():
            lines.append(
                ",".join(
                    str(row[column])
                    for column in ("datetime", "open", "high", "low", "close", "volume")
                )
            )
        handle = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
            newline="",
        )
        with handle:
            handle.write("\n".join(lines) + "\n")
        return Path(handle.name)

    def _parquet_source(self) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".parquet")
        handle.close()
        path = Path(handle.name)
        pd.DataFrame(self._rows()).to_parquet(path, index=False)
        return path

    def _duckdb_source(self) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb")
        handle.close()
        path = Path(handle.name)
        path.unlink(missing_ok=True)
        rows = self._rows()
        frame = pd.DataFrame(rows)
        with duckdb.connect(str(path)) as connection:
            connection.execute("CREATE TABLE candles AS SELECT * FROM frame")
        return path

    def _upper_layer_files(self) -> list[Path]:
        return [
            Path("application") / "replay_service.py",
            Path("application") / "research_lab_service.py",
            Path("dashboard_app.py"),
        ]

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
