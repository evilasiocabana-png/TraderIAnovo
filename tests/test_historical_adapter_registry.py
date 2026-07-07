"""Testes do registry oficial de adapters historicos."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from market_data import HistoricalDataProvider, HistoricalDataSourceResult
from market_data.adapters import HistoricalDataAdapter
from market_data.adapters.historical_adapter_registry import (
    HistoricalAdapterRegistry,
    create_default_historical_adapter_registry,
)


REGISTRY_PATH = Path("market_data/adapters/historical_adapter_registry.py")
PROVIDER_PATH = Path("market_data/historical_data_provider.py")


class HistoricalAdapterRegistryTest(unittest.TestCase):
    """Valida registro e resolucao de adapters por contrato."""

    def test_registry_importa_e_instancia(self) -> None:
        registry = HistoricalAdapterRegistry()

        self.assertIsInstance(registry, HistoricalAdapterRegistry)
        self.assertEqual(registry.list_adapters(), [])

    def test_adapters_podem_ser_registrados(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = _FakeAdapter("fixture", ("fixture",))

        registry.register(adapter)

        self.assertEqual(registry.list_adapters(), ["fixture"])
        self.assertTrue(registry.has_adapter("fixture"))

    def test_adapter_duplicado_e_tratado(self) -> None:
        registry = HistoricalAdapterRegistry()
        registry.register(_FakeAdapter("fixture", ("fixture",)))

        with self.assertRaisesRegex(ValueError, "duplicado"):
            registry.register(_FakeAdapter("fixture", ("other",)))

        with self.assertRaisesRegex(ValueError, "Formato"):
            registry.register(_FakeAdapter("other", ("fixture",)))

    def test_adapter_correto_e_resolvido_por_formato(self) -> None:
        registry = HistoricalAdapterRegistry()
        csv = _FakeAdapter("csv", ("csv",))
        parquet = _FakeAdapter("parquet", ("parquet",))
        registry.register(parquet)
        registry.register(csv)

        self.assertIs(registry.get_adapter_for_format("CSV"), csv)
        self.assertIs(registry.get_adapter_for_format("parquet"), parquet)

    def test_adapter_e_resolvido_por_dataset_metadata(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = _FakeAdapter("parquet", ("parquet",))
        registry.register(adapter)

        resolved = registry.get_adapter_for_dataset({"format": "PARQUET"})

        self.assertIs(resolved, adapter)

    def test_erro_claro_quando_formato_nao_e_suportado(self) -> None:
        registry = HistoricalAdapterRegistry()

        with self.assertRaisesRegex(KeyError, "Nenhum adapter historico suporta"):
            registry.get_adapter_for_format("mt5")

        with self.assertRaisesRegex(KeyError, "Nenhum adapter historico suporta"):
            registry.get_adapter_for_dataset({"format": "mt5"})

    def test_unregister_remove_adapter(self) -> None:
        registry = HistoricalAdapterRegistry()
        registry.register(_FakeAdapter("csv", ("csv",)))

        registry.unregister("CSV")

        self.assertEqual(registry.list_adapters(), [])
        with self.assertRaisesRegex(KeyError, "nao registrado"):
            registry.unregister("CSV")

    def test_registry_default_contem_adapters_conhecidos(self) -> None:
        registry = create_default_historical_adapter_registry()

        self.assertEqual(registry.list_adapters(), ["csv", "duckdb", "parquet"])
        self.assertTrue(registry.has_adapter("csv"))
        self.assertTrue(registry.has_adapter("parquet"))
        self.assertTrue(registry.has_adapter("duckdb"))

    def test_provider_usa_registry_e_abstracao(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = _FakeAdapter("csv", ("csv",))
        registry.register(adapter)
        provider = HistoricalDataProvider(adapter_registry=registry)

        self.assertIs(provider.resolve_adapter("CSV"), adapter)

    def test_provider_nao_conhece_adapters_concretos(self) -> None:
        source = PROVIDER_PATH.read_text(encoding="utf-8")

        self.assertIn("HistoricalAdapterRegistry", source)
        self.assertNotIn("CsvHistoricalDataSource", source)
        self.assertNotIn("ParquetHistoricalDataAdapter", source)
        self.assertNotIn("DuckDBHistoricalDataAdapter", source)

    def test_registry_nao_importa_acoplamentos_proibidos(self) -> None:
        imports = self._imports(REGISTRY_PATH)
        calls = self._calls(REGISTRY_PATH)
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
    def __init__(self, name: str, formats: tuple[str, ...]) -> None:
        self.adapter_label = name
        self.supported_formats = formats

    def load(self, source: object) -> HistoricalDataSourceResult:
        return HistoricalDataSourceResult(candles=[], errors=[])


if __name__ == "__main__":
    unittest.main()
