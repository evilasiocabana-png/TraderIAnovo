"""Testes do importador de datasets historicos."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from market_data.catalog import HistoricalDatasetCatalog
from market_data.historical_importer import HistoricalImporter
from market_data.validation.historical_dataset_validator import (
    HistoricalDatasetValidator,
)


class HistoricalImporterTest(unittest.TestCase):
    """Valida importacao OHLCV para estrutura interna."""

    def test_importa_csv_ohlcv_para_dataset_interno(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            importer = HistoricalImporter(root=Path(tmp) / "datasets")

            result = importer.import_csv(
                Path("tests/fixtures/historical_data/wdo_1m_sample.csv"),
                symbol="WDO",
                timeframe="1m",
            )

            self.assertTrue(result.success)
            self.assertEqual(result.imported_candles, 2)
            self.assertEqual(result.dataset.start_date, "2025-01-01 09:00")
            self.assertEqual(result.dataset.end_date, "2025-01-01 09:01")
            self.assertTrue(Path(result.data_path).is_file())
            self.assertTrue(Path(result.metadata_path).is_file())

    def test_remove_duplicidades_por_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "duplicated.csv"
            source.write_text(
                "\n".join(
                    [
                        "timestamp,open,high,low,close,volume",
                        "2025-01-01 09:00,100,102,99,101,1000",
                        "2025-01-01 09:00,100,102,99,101,1000",
                        "2025-01-01 09:01,101,103,100,102,1100",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            importer = HistoricalImporter(root=Path(tmp) / "datasets")

            result = importer.import_csv(source, symbol="WDO", timeframe="1m")

            self.assertTrue(result.success)
            self.assertEqual(result.imported_candles, 2)
            self.assertEqual(result.duplicated_candles_removed, 1)

    def test_metadados_sao_validos_e_catalogaveis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            importer = HistoricalImporter(root=root)

            result = importer.import_csv(
                Path("tests/fixtures/historical_data/wdo_1m_sample.csv"),
                symbol="WDO",
                timeframe="1m",
            )

            metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
            validation = HistoricalDatasetValidator().validate(metadata)
            catalog = HistoricalDatasetCatalog(root)

            self.assertTrue(validation.is_valid)
            self.assertTrue(catalog.dataset_exists("WDO", "1m", "2025"))
            self.assertEqual(catalog.get_dataset_metadata("WDO", "1m", "2025")["candle_count"], 2)

    def test_rejeita_csv_invalido_sem_criar_dataset_utilizavel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "invalid.csv"
            source.write_text("foo,bar\n1,2\n", encoding="utf-8")
            importer = HistoricalImporter(root=Path(tmp) / "datasets")

            result = importer.import_csv(source, symbol="WDO", timeframe="1m")

            self.assertFalse(result.success)
            self.assertEqual(result.imported_candles, 0)
            self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
