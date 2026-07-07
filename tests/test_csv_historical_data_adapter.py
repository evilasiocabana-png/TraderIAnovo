"""Contrato do adapter CSV historico."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from market_data.adapters import HistoricalDataAdapter
from market_data.adapters.csv_historical_data_adapter import CsvHistoricalDataAdapter
from market_data.adapters.historical_adapter_registry import (
    HistoricalAdapterRegistry,
    create_default_historical_adapter_registry,
)
from market_data.historical_data_provider import HistoricalDataProvider


ADAPTER_PATH = Path("market_data/adapters/csv_historical_data_adapter.py")
FIXTURE_PATH = Path("tests/fixtures/historical_data/wdo_1m_sample.csv")
PROVIDER_PATH = Path("market_data/historical_data_provider.py")
UPPER_LAYER_FILES = (
    Path("application/dashboard_service.py"),
    Path("application/replay_service.py"),
    Path("application/research_lab_service.py"),
    Path("dashboard_app.py"),
)


class CsvHistoricalDataAdapterTest(unittest.TestCase):
    """Valida isolamento do adapter CSV."""

    def test_adapter_importa_e_instancia(self) -> None:
        adapter = CsvHistoricalDataAdapter()

        self.assertIsInstance(adapter, CsvHistoricalDataAdapter)

    def test_adapter_implementa_interface_base(self) -> None:
        adapter = CsvHistoricalDataAdapter()

        self.assertIsInstance(adapter, HistoricalDataAdapter)

    def test_suporta_formato_csv(self) -> None:
        adapter = CsvHistoricalDataAdapter()

        self.assertTrue(adapter.supports("csv"))
        self.assertTrue(adapter.supports("CSV"))
        self.assertTrue(adapter.can_handle({"format": "csv"}))
        self.assertTrue(adapter.can_handle({"provider": "CSV"}))

    def test_nao_suporta_formatos_nao_csv(self) -> None:
        adapter = CsvHistoricalDataAdapter()

        self.assertFalse(adapter.supports("parquet"))
        self.assertFalse(adapter.supports("duckdb"))
        self.assertFalse(adapter.can_handle({"format": "parquet"}))

    def test_expoe_nome_e_metadados_basicos(self) -> None:
        adapter = CsvHistoricalDataAdapter()

        metadata = adapter.get_metadata("dataset-ref")

        self.assertEqual(adapter.adapter_name(), "csv")
        self.assertEqual(metadata["adapter"], "csv")
        self.assertEqual(metadata["supported_formats"], ["csv"])
        self.assertNotIn("candles", metadata)

    def test_le_fixture_csv_minima(self) -> None:
        result = CsvHistoricalDataAdapter().load_candles(FIXTURE_PATH)

        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.candles), 2)
        self.assertEqual(result.candles[0].data, "2025-01-01 09:00")
        self.assertEqual(result.candles[0].abertura, 100.0)
        self.assertEqual(result.candles[1].fechamento, 102.0)

    def test_retorna_estrutura_padronizada_sem_dataframe(self) -> None:
        result = CsvHistoricalDataAdapter().load_candles(FIXTURE_PATH)

        self.assertTrue(hasattr(result, "candles"))
        self.assertTrue(hasattr(result, "errors"))
        self.assertFalse(hasattr(result, "dataframe"))
        self.assertEqual(result.candles[0].volume, 1000)

    def test_falha_com_erro_claro_para_arquivo_inexistente(self) -> None:
        result = CsvHistoricalDataAdapter().load_candles(
            Path("tests/fixtures/historical_data/inexistente.csv")
        )

        self.assertEqual(result.candles, [])
        self.assertTrue(result.errors)
        self.assertIn("Arquivo CSV invalido", result.errors[0])

    def test_falha_com_erro_claro_para_coluna_obrigatoria_ausente(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.csv"
            path.write_text(
                "\n".join(
                    [
                        "timestamp,open,high,low,close",
                        "2025-01-01 09:00,100,101,99,100.5",
                    ]
                ),
                encoding="utf-8",
            )

            result = CsvHistoricalDataAdapter().load_candles(path)

        self.assertEqual(result.candles, [])
        self.assertIn("CSV sem coluna obrigatoria.", result.errors)

    def test_pode_ser_registrado_no_registry(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = CsvHistoricalDataAdapter()

        registry.register(adapter)

        self.assertIs(registry.get_adapter_for_format("csv"), adapter)
        self.assertTrue(registry.has_adapter("CSV"))

    def test_registry_default_resolve_csv_pelo_adapter_formal(self) -> None:
        registry = create_default_historical_adapter_registry()

        adapter = registry.get_adapter_for_format("csv")

        self.assertIsInstance(adapter, CsvHistoricalDataAdapter)

    def test_provider_resolve_csv_via_registry(self) -> None:
        provider = HistoricalDataProvider()

        adapter = provider.resolve_adapter("csv")

        self.assertIsInstance(adapter, CsvHistoricalDataAdapter)

    def test_provider_nao_importa_adapter_csv_concreto(self) -> None:
        source = PROVIDER_PATH.read_text(encoding="utf-8")

        self.assertIn("HistoricalAdapterRegistry", source)
        self.assertNotIn("CsvHistoricalDataAdapter", source)

    def test_camadas_superiores_nao_importam_adapter_csv(self) -> None:
        forbidden = {
            "market_data.adapters.csv_historical_data_adapter",
            "CsvHistoricalDataAdapter",
        }

        for path in UPPER_LAYER_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                source = path.read_text(encoding="utf-8")
                self.assertTrue(forbidden.isdisjoint(imports))
                self.assertNotIn("CsvHistoricalDataAdapter", source)

    def test_camadas_superiores_nao_acessam_csv_diretamente(self) -> None:
        paths = [
            *UPPER_LAYER_FILES,
            *Path("domain").rglob("*.py"),
            *Path("strategies").rglob("*.py"),
            *Path("research").rglob("*.py"),
            *Path("replay").rglob("*.py"),
        ]
        forbidden_calls = {"read_csv", "load_csv"}
        forbidden_text = ("csv.DictReader",)

        for path in paths:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                calls = self._calls(path)
                self.assertTrue(forbidden_calls.isdisjoint(calls))
                self.assertEqual(
                    [item for item in forbidden_text if item in source],
                    [],
                )

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
