"""Contrato publico do HistoricalDataProvider."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from market_data.catalog import HistoricalDatasetCatalog
from market_data.historical_data_provider import HistoricalDataProvider
from market_data.historical_data_source import HistoricalDataSource


PROVIDER_PATH = Path("market_data/historical_data_provider.py")
APPLICATION_FILES = (
    Path("application/dashboard_service.py"),
    Path("application/replay_service.py"),
    Path("application/research_lab_service.py"),
)


class HistoricalDataProviderContractTest(unittest.TestCase):
    """Protege a fachada autorizada para consumo historico."""

    def test_provider_importa_e_instancia(self) -> None:
        provider = HistoricalDataProvider()

        self.assertIsInstance(provider, HistoricalDataProvider)

    def test_api_publica_existe(self) -> None:
        provider = HistoricalDataProvider()
        expected_methods = [
            "get_dataset",
            "dataset_exists",
            "list_datasets",
            "list_symbols",
            "list_timeframes",
            "get_metadata",
            "load_dataset",
            "resolve_adapter",
        ]

        for method in expected_methods:
            with self.subTest(method=method):
                self.assertTrue(callable(getattr(provider, method, None)))

    def test_provider_utiliza_catalogo_para_descoberta(self) -> None:
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
            provider = HistoricalDataProvider(
                dataset_catalog=HistoricalDatasetCatalog(root)
            )

            self.assertEqual(provider.list_symbols(), ["WDO"])
            self.assertEqual(provider.list_timeframes("WDO"), ["1m"])
            self.assertTrue(provider.dataset_exists("WDO", "1m", "2025"))
            self.assertEqual(provider.get_metadata("WDO", "1m", "2025")["symbol"], "WDO")
            self.assertEqual(len(provider.list_datasets()), 1)

    def test_resolve_adapter_retorna_porta_abstrata(self) -> None:
        provider = HistoricalDataProvider()

        adapter = provider.resolve_adapter("csv")

        self.assertIsInstance(adapter, HistoricalDataSource)

    def test_consumidor_nao_precisa_conhecer_formato_fisico(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "datasets"
            (root / "WDO" / "1m" / "2025").mkdir(parents=True)
            provider = HistoricalDataProvider(
                dataset_catalog=HistoricalDatasetCatalog(root)
            )

            dataset = provider.get_dataset("WDO", "1m", "2025")

            self.assertIsNotNone(dataset)
            self.assertIn("symbol", dataset)
            self.assertIn("timeframe", dataset)
            self.assertIn("period", dataset)
            self.assertNotIn("candles", dataset)

    def test_provider_nao_importa_acoplamentos_proibidos(self) -> None:
        imports = self._imports(PROVIDER_PATH)
        calls = self._calls(PROVIDER_PATH)
        forbidden_imports = {
            "pandas",
            "duckdb",
            "pyarrow",
            "csv",
            "dashboard_app",
            "replay",
            "research",
            "streamlit",
            "core.broker",
            "MetaTrader5",
            "domain",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)

    def test_servicos_de_aplicacao_nao_conhecem_adapters(self) -> None:
        forbidden_imports = {
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
        }

        for path in APPLICATION_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} conhece adapters: {sorted(forbidden_imports & imports)}",
                )

    def test_replay_research_dashboard_usam_provider_sem_adapters(self) -> None:
        for path in APPLICATION_FILES:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                self.assertIn("HistoricalDataProvider", source)
                self.assertNotIn("CsvHistoricalDataSource", source)
                self.assertNotIn("ParquetHistoricalDataAdapter", source)
                self.assertNotIn("DuckDBHistoricalDataAdapter", source)

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
                imports.add(node.module.split(".", 1)[0])
                imports.update(alias.name for alias in node.names)
        return imports

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


if __name__ == "__main__":
    unittest.main()
