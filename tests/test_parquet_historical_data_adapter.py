"""Contrato do adapter Parquet historico."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from market_data.adapters import HistoricalDataAdapter
from market_data.adapters.historical_adapter_registry import (
    HistoricalAdapterRegistry,
    create_default_historical_adapter_registry,
)
from market_data.adapters.parquet_historical_data_adapter import (
    ParquetHistoricalDataAdapter,
)
from market_data.historical_data_provider import HistoricalDataProvider


ADAPTER_PATH = Path("market_data/adapters/parquet_historical_data_adapter.py")
PROVIDER_PATH = Path("market_data/historical_data_provider.py")
UPPER_LAYER_FILES = (
    Path("application/dashboard_service.py"),
    Path("application/replay_service.py"),
    Path("application/research_lab_service.py"),
    Path("dashboard_app.py"),
)


class ParquetHistoricalDataAdapterTest(unittest.TestCase):
    """Valida isolamento do adapter Parquet."""

    def test_adapter_importa_e_instancia(self) -> None:
        adapter = ParquetHistoricalDataAdapter()

        self.assertIsInstance(adapter, ParquetHistoricalDataAdapter)

    def test_adapter_implementa_interface_base(self) -> None:
        adapter = ParquetHistoricalDataAdapter()

        self.assertIsInstance(adapter, HistoricalDataAdapter)

    def test_suporta_formato_parquet(self) -> None:
        adapter = ParquetHistoricalDataAdapter()

        self.assertTrue(adapter.supports("parquet"))
        self.assertTrue(adapter.supports("PARQUET"))
        self.assertTrue(adapter.can_handle({"format": "parquet"}))
        self.assertTrue(adapter.can_handle({"provider": "PARQUET"}))

    def test_nao_suporta_formatos_nao_parquet(self) -> None:
        adapter = ParquetHistoricalDataAdapter()

        self.assertFalse(adapter.supports("csv"))
        self.assertFalse(adapter.supports("duckdb"))
        self.assertFalse(adapter.can_handle({"format": "csv"}))

    def test_expoe_nome_e_metadados_basicos(self) -> None:
        adapter = ParquetHistoricalDataAdapter()

        metadata = adapter.get_metadata("dataset-ref")

        self.assertEqual(adapter.adapter_name(), "parquet")
        self.assertEqual(metadata["adapter"], "parquet")
        self.assertEqual(metadata["supported_formats"], ["parquet"])
        self.assertNotIn("candles", metadata)

    def test_pode_ser_registrado_no_registry(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = ParquetHistoricalDataAdapter()

        registry.register(adapter)

        self.assertIs(registry.get_adapter_for_format("parquet"), adapter)
        self.assertTrue(registry.has_adapter("PARQUET"))

    def test_registry_default_resolve_parquet_pelo_adapter_formal(self) -> None:
        registry = create_default_historical_adapter_registry()

        adapter = registry.get_adapter_for_format("parquet")

        self.assertIsInstance(adapter, ParquetHistoricalDataAdapter)

    def test_provider_resolve_parquet_via_registry(self) -> None:
        provider = HistoricalDataProvider()

        adapter = provider.resolve_adapter("parquet")

        self.assertIsInstance(adapter, ParquetHistoricalDataAdapter)

    def test_provider_nao_importa_adapter_parquet_concreto(self) -> None:
        source = PROVIDER_PATH.read_text(encoding="utf-8")

        self.assertIn("HistoricalAdapterRegistry", source)
        self.assertNotIn("ParquetHistoricalDataAdapter", source)

    def test_camadas_superiores_nao_importam_adapter_parquet(self) -> None:
        forbidden = {
            "market_data.adapters.parquet_historical_data_adapter",
            "ParquetHistoricalDataAdapter",
        }

        for path in UPPER_LAYER_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                source = path.read_text(encoding="utf-8")
                self.assertTrue(forbidden.isdisjoint(imports))
                self.assertNotIn("ParquetHistoricalDataAdapter", source)

    def test_adapter_nao_acessa_operacao_real(self) -> None:
        source = ADAPTER_PATH.read_text(encoding="utf-8").lower()
        forbidden_terms = [
            "dashboard",
            "replay",
            "research",
            "streamlit",
            "broker",
            "mt5",
            "metatrader",
            "corretora",
            "send_order",
            "order_send",
            "envio de ordens",
            "operacao real",
            "estrateg",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

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


if __name__ == "__main__":
    unittest.main()
