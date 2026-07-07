"""Testes do catalogo de datasets historicos."""

import ast
import builtins
import json
import tempfile
import unittest
from pathlib import Path

from market_data.catalog import (
    HistoricalDatasetCatalog as StructuralHistoricalDatasetCatalog,
    HistoricalDatasetRecord,
)
from market_data import (
    CsvHistoricalDataSource,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    HistoricalDataSourceRegistry,
)


class HistoricalDatasetCatalogTest(unittest.TestCase):
    """Valida descoberta de datasets sem expor origem fisica."""

    def test_catalogo_lista_metadados_sem_candles(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata(dataset_id="wdo_1m_2026", provider="csv")

        catalog.register_dataset(metadata)
        datasets = catalog.list_datasets()

        self.assertEqual(datasets, [metadata])
        self.assertEqual(datasets[0].dataset_id, "wdo_1m_2026")
        self.assertEqual(datasets[0].ativo, "WDO")
        self.assertEqual(datasets[0].timeframe, "1m")
        self.assertEqual(datasets[0].start_date, "2026-06-01")
        self.assertEqual(datasets[0].end_date, "2026-06-26")
        self.assertEqual(datasets[0].estimated_candles, 1200)
        self.assertEqual(datasets[0].provider, "csv")
        self.assertFalse(hasattr(datasets[0], "candles"))

    def test_catalogo_usa_csv_como_provider_default(self) -> None:
        catalog = HistoricalDatasetCatalog()

        self.assertIn("csv", catalog.available_providers())

    def test_catalogo_lista_parquet_como_provider_registrado(self) -> None:
        catalog = HistoricalDatasetCatalog()

        self.assertIn("parquet", catalog.available_providers())

    def test_catalogo_lista_duckdb_como_provider_registrado(self) -> None:
        catalog = HistoricalDatasetCatalog()

        self.assertIn("duckdb", catalog.available_providers())

    def test_catalogo_lista_datasets_csv_parquet_e_duckdb_com_mesmo_contrato(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        csv_metadata = self._metadata(dataset_id="wdo_csv_1m", provider="csv")
        parquet_metadata = self._metadata(
            dataset_id="wdo_parquet_1m",
            provider="parquet",
        )
        duckdb_metadata = self._metadata(
            dataset_id="wdo_duckdb_1m",
            provider="duckdb",
        )

        catalog.register_dataset(csv_metadata, source="origem_csv_opaca")
        catalog.register_dataset(parquet_metadata, source="origem_parquet_opaca")
        catalog.register_dataset(duckdb_metadata, source="origem_duckdb_opaca")

        datasets = catalog.list_datasets()

        self.assertEqual(datasets, [csv_metadata, duckdb_metadata, parquet_metadata])
        for metadata in datasets:
            with self.subTest(dataset_id=metadata.dataset_id):
                self.assertIsInstance(metadata, HistoricalDatasetMetadata)
                self.assertTrue(metadata.dataset_id)
                self.assertEqual(metadata.ativo, "WDO")
                self.assertEqual(metadata.timeframe, "1m")
                self.assertEqual(metadata.start_date, "2026-06-01")
                self.assertEqual(metadata.end_date, "2026-06-26")
                self.assertEqual(metadata.estimated_candles, 1200)
                self.assertIn(metadata.provider, {"csv", "parquet", "duckdb"})
                self.assertFalse(hasattr(metadata, "source"))
                self.assertFalse(hasattr(metadata, "candles"))

    def test_catalogo_filtra_dataset_parquet_e_duckdb_por_provider(self) -> None:
        catalog = HistoricalDatasetCatalog()
        csv_metadata = self._metadata(dataset_id="wdo_csv_1m", provider="csv")
        parquet_metadata = self._metadata(
            dataset_id="wdo_parquet_1m",
            provider="parquet",
        )
        duckdb_metadata = self._metadata(
            dataset_id="wdo_duckdb_1m",
            provider="duckdb",
        )

        catalog.register_dataset(csv_metadata, source="origem_csv_opaca")
        catalog.register_dataset(parquet_metadata, source="origem_parquet_opaca")
        catalog.register_dataset(duckdb_metadata, source="origem_duckdb_opaca")

        self.assertEqual(catalog.list_datasets(provider="PARQUET"), [parquet_metadata])
        self.assertEqual(catalog.list_datasets(provider="DUCKDB"), [duckdb_metadata])
        self.assertEqual(
            catalog.get_dataset_source("wdo_parquet_1m"),
            "origem_parquet_opaca",
        )
        self.assertEqual(
            catalog.get_dataset_source("wdo_duckdb_1m"),
            "origem_duckdb_opaca",
        )

    def test_catalogo_filtra_datasets_por_provider(self) -> None:
        registry = HistoricalDataSourceRegistry()
        registry.register("csv", CsvHistoricalDataSource)
        registry.register("duckdb", CsvHistoricalDataSource)
        catalog = HistoricalDatasetCatalog(registry=registry)
        csv_metadata = self._metadata(dataset_id="csv_dataset", provider="csv")
        duckdb_metadata = self._metadata(
            dataset_id="duckdb_dataset",
            provider="duckdb",
        )

        catalog.register_dataset(duckdb_metadata)
        catalog.register_dataset(csv_metadata)

        self.assertEqual(catalog.list_datasets(provider="CSV"), [csv_metadata])
        self.assertEqual(catalog.list_datasets(provider="duckdb"), [duckdb_metadata])

    def test_catalogo_rejeita_provider_nao_registrado(self) -> None:
        catalog = HistoricalDatasetCatalog()

        with self.assertRaisesRegex(KeyError, "mt5"):
            catalog.register_dataset(
                self._metadata(dataset_id="mt5_dataset", provider="mt5")
            )

    def test_catalogo_busca_dataset_por_id(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata(dataset_id="wdo_5m_2026", provider="csv")
        catalog.register_dataset(metadata)

        self.assertEqual(catalog.get_dataset("wdo_5m_2026"), metadata)
        self.assertIsNone(catalog.get_dataset("inexistente"))

    def test_catalogo_guarda_origem_opaca_sem_expor_nos_metadados(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata(dataset_id="wdo_1m_2026", provider="csv")

        catalog.register_dataset(metadata, source="origem_opaca")

        self.assertEqual(catalog.get_dataset_source("wdo_1m_2026"), "origem_opaca")
        self.assertIsNone(catalog.get_dataset_source("inexistente"))
        self.assertFalse(hasattr(catalog.list_datasets()[0], "source"))

    def test_catalogo_nao_usa_listagem_de_arquivos(self) -> None:
        source = Path("market_data/historical_dataset_catalog.py").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("Path", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("glob", source)
        self.assertNotIn("listdir", source)
        self.assertNotIn("iterdir", source)

    def test_replay_e_research_nao_listam_diretorios_para_datasets(self) -> None:
        for path in self._upper_layer_files():
            calls = self._calls(path)
            self.assertNotIn("glob", calls)
            self.assertNotIn("listdir", calls)
            self.assertNotIn("iterdir", calls)

    def _metadata(
        self,
        dataset_id: str,
        provider: str,
    ) -> HistoricalDatasetMetadata:
        return HistoricalDatasetMetadata(
            dataset_id=dataset_id,
            ativo="WDO",
            timeframe="1m",
            start_date="2026-06-01",
            end_date="2026-06-26",
            estimated_candles=1200,
            provider=provider,
        )

    def _upper_layer_files(self) -> list[Path]:
        return [
            Path("application") / "replay_service.py",
            Path("application") / "research_lab_service.py",
        ]

    def _calls(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return calls


class StructuralHistoricalDatasetCatalogTest(unittest.TestCase):
    """Valida catalogo estrutural sem leitura de candles."""

    def test_catalogo_importa_e_instancia(self) -> None:
        catalog = StructuralHistoricalDatasetCatalog()

        self.assertIsInstance(catalog, StructuralHistoricalDatasetCatalog)

    def test_ausencia_de_datasets_reais_nao_gera_erro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            root.mkdir()
            catalog = StructuralHistoricalDatasetCatalog(root)

            self.assertEqual(catalog.list_symbols(), [])
            self.assertEqual(catalog.list_datasets(), [])
            self.assertEqual(catalog.validate_structure()["valid"], True)

    def test_diretorios_validos_sao_encontrados(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            dataset_dir = root / "WDO" / "1m" / "2025"
            dataset_dir.mkdir(parents=True)
            catalog = StructuralHistoricalDatasetCatalog(root)

            self.assertEqual(catalog.list_symbols(), ["WDO"])
            self.assertEqual(catalog.list_timeframes("WDO"), ["1m"])
            self.assertEqual(catalog.list_available_periods("WDO", "1m"), ["2025"])
            self.assertTrue(catalog.dataset_exists("WDO", "1m", "2025"))

    def test_list_datasets_retorna_registros_estruturais(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            (root / "WDO" / "1m" / "2025").mkdir(parents=True)
            catalog = StructuralHistoricalDatasetCatalog(root)

            datasets = catalog.list_datasets()

            self.assertEqual(len(datasets), 1)
            self.assertIsInstance(datasets[0], HistoricalDatasetRecord)
            self.assertEqual(datasets[0].symbol, "WDO")
            self.assertEqual(datasets[0].timeframe, "1m")
            self.assertEqual(datasets[0].period, "2025")

    def test_metadados_sao_retornados_sem_carregar_candles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            dataset_dir = root / "WDO" / "1m" / "2025"
            dataset_dir.mkdir(parents=True)
            (dataset_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "symbol": "WDO",
                        "timeframe": "1m",
                        "source": "fixture",
                        "exchange": "B3",
                        "timezone": "America/Sao_Paulo",
                        "first_timestamp": "2025-01-01T09:00:00-03:00",
                        "last_timestamp": "2025-01-01T09:01:00-03:00",
                        "candle_count": 2,
                        "format": "parquet",
                        "version": "1.0",
                    }
                ),
                encoding="utf-8",
            )
            catalog = StructuralHistoricalDatasetCatalog(root)

            metadata = catalog.get_dataset_metadata("WDO", "1m", "2025")

            self.assertIsNotNone(metadata)
            self.assertEqual(metadata["symbol"], "WDO")
            self.assertEqual(metadata["timeframe"], "1m")
            self.assertEqual(metadata["source"], "fixture")
            self.assertEqual(metadata["candle_count"], 2)
            self.assertNotIn("candles", metadata)

    def test_catalogacao_nao_abre_arquivos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            (root / "WDO" / "1m" / "2025").mkdir(parents=True)
            catalog = StructuralHistoricalDatasetCatalog(root)
            original_open = builtins.open

            def fail_open(*args, **kwargs):  # type: ignore[no-untyped-def]
                raise AssertionError("Catalogacao nao deve abrir arquivos.")

            builtins.open = fail_open
            try:
                self.assertEqual(catalog.list_symbols(), ["WDO"])
                self.assertEqual(len(catalog.list_datasets()), 1)
                self.assertTrue(catalog.dataset_exists("WDO", "1m", "2025"))
            finally:
                builtins.open = original_open

    def test_acoplamentos_proibidos_nao_sao_importados(self) -> None:
        source_path = Path("market_data/catalog/historical_dataset_catalog.py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        calls: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)

        forbidden_imports = {
            "pandas",
            "duckdb",
            "pyarrow",
            "csv",
            "replay",
            "research",
            "dashboard_app",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)


if __name__ == "__main__":
    unittest.main()
