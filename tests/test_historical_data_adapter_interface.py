"""Contrato comum dos adapters de dados historicos."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from market_data import (
    CsvHistoricalDataSource,
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    HistoricalDataSourceResult,
    ParquetHistoricalDataAdapter,
)
from market_data.adapters import HistoricalDataAdapter


INTERFACE_PATH = Path("market_data/adapters/historical_data_adapter.py")
PROVIDER_PATH = Path("market_data/historical_data_provider.py")
APPLICATION_FILES = (
    Path("application/dashboard_service.py"),
    Path("application/replay_service.py"),
    Path("application/research_lab_service.py"),
)


class HistoricalDataAdapterInterfaceTest(unittest.TestCase):
    """Protege a interface comum dos adapters historicos."""

    def test_interface_importa_sem_excecao(self) -> None:
        self.assertIsNotNone(HistoricalDataAdapter)

    def test_contrato_publico_existe(self) -> None:
        expected_methods = {
            "supports",
            "can_handle",
            "get_metadata",
            "load_candles",
            "adapter_name",
        }

        self.assertTrue(expected_methods.issubset(self._public_methods(INTERFACE_PATH)))

    def test_interface_nao_acessa_infraestrutura_fisica(self) -> None:
        imports = self._imports(INTERFACE_PATH)
        calls = self._calls(INTERFACE_PATH)
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
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)

    def test_adapters_concretos_respeitam_interface(self) -> None:
        adapters = (
            CsvHistoricalDataSource(),
            ParquetHistoricalDataAdapter(),
            DuckDBHistoricalDataAdapter(),
        )

        for adapter in adapters:
            with self.subTest(adapter=adapter.__class__.__name__):
                self.assertIsInstance(adapter, HistoricalDataAdapter)
                self.assertTrue(adapter.adapter_name())
                self.assertTrue(adapter.supports(adapter.adapter_name()))
                self.assertTrue(adapter.can_handle({"format": adapter.adapter_name()}))
                metadata = adapter.get_metadata("origem-opaca")
                self.assertEqual(metadata["adapter"], adapter.adapter_name())

    def test_load_candles_delega_para_contrato_load(self) -> None:
        adapter = _FakeAdapter()

        result = adapter.load_candles("dataset-ref")

        self.assertIsInstance(result, HistoricalDataSourceResult)
        self.assertEqual(adapter.loaded_refs, ["dataset-ref"])

    def test_provider_depende_da_abstracao_de_adapter(self) -> None:
        imports = self._imports(PROVIDER_PATH)
        source = PROVIDER_PATH.read_text(encoding="utf-8")

        self.assertIn("market_data.adapters", imports)
        self.assertIn("HistoricalDataAdapter", source)
        self.assertNotIn("CsvHistoricalDataSource", source)
        self.assertNotIn("ParquetHistoricalDataAdapter", source)
        self.assertNotIn("DuckDBHistoricalDataAdapter", source)

    def test_provider_pode_receber_adapter_via_abstracao(self) -> None:
        adapter = _FakeAdapter()
        provider = HistoricalDataProvider(data_source=adapter)

        dataset = provider.load("origem", symbol="WDO", timeframe="1m")

        self.assertEqual(adapter.loaded_refs, ["origem"])
        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")

    def test_consumidores_nao_dependem_de_adapters_concretos(self) -> None:
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
                source = path.read_text(encoding="utf-8")
                self.assertTrue(forbidden_imports.isdisjoint(imports))
                self.assertNotIn("CsvHistoricalDataSource", source)
                self.assertNotIn("ParquetHistoricalDataAdapter", source)
                self.assertNotIn("DuckDBHistoricalDataAdapter", source)

    def _public_methods(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }

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


class _FakeAdapter(HistoricalDataAdapter):
    supported_formats = ("fake",)
    adapter_label = "fake"

    def __init__(self) -> None:
        self.loaded_refs: list[object] = []

    def load(self, source: object) -> HistoricalDataSourceResult:
        self.loaded_refs.append(source)
        return HistoricalDataSourceResult(candles=[], errors=[])


if __name__ == "__main__":
    unittest.main()
