"""Testes do adapter DuckDB de Market Data."""

import ast
from pathlib import Path
import tempfile
import unittest

import duckdb
import pandas as pd

from market_data import (
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    create_historical_data_source,
)
from market_data.adapters import HistoricalDataAdapter
from market_data.adapters.duckdb_historical_data_adapter import (
    DuckDBHistoricalDataAdapter as FormalDuckDBHistoricalDataAdapter,
)
from market_data.adapters.historical_adapter_registry import (
    HistoricalAdapterRegistry,
    create_default_historical_adapter_registry,
)


ADAPTER_PATH = Path("market_data/adapters/duckdb_historical_data_adapter.py")
PROVIDER_PATH = Path("market_data/historical_data_provider.py")


class DuckDBHistoricalDataAdapterTest(unittest.TestCase):
    """Valida leitura DuckDB isolada no adapter."""

    def test_adapter_formal_importa_e_instancia(self) -> None:
        adapter = FormalDuckDBHistoricalDataAdapter()

        self.assertIsInstance(adapter, FormalDuckDBHistoricalDataAdapter)

    def test_adapter_formal_implementa_interface_base(self) -> None:
        adapter = FormalDuckDBHistoricalDataAdapter()

        self.assertIsInstance(adapter, HistoricalDataAdapter)

    def test_adapter_formal_suporta_formato_duckdb(self) -> None:
        adapter = FormalDuckDBHistoricalDataAdapter()

        self.assertTrue(adapter.supports("duckdb"))
        self.assertTrue(adapter.supports("DUCKDB"))
        self.assertTrue(adapter.can_handle({"format": "duckdb"}))
        self.assertTrue(adapter.can_handle({"provider": "DUCKDB"}))

    def test_adapter_formal_nao_suporta_formatos_nao_duckdb(self) -> None:
        adapter = FormalDuckDBHistoricalDataAdapter()

        self.assertFalse(adapter.supports("csv"))
        self.assertFalse(adapter.supports("parquet"))
        self.assertFalse(adapter.can_handle({"format": "csv"}))

    def test_adapter_formal_expoe_nome_e_metadados_basicos(self) -> None:
        adapter = FormalDuckDBHistoricalDataAdapter()

        metadata = adapter.get_metadata("dataset-ref")

        self.assertEqual(adapter.adapter_name(), "duckdb")
        self.assertEqual(metadata["adapter"], "duckdb")
        self.assertEqual(metadata["supported_formats"], ["duckdb"])
        self.assertNotIn("candles", metadata)

    def test_adapter_formal_pode_ser_registrado_no_registry(self) -> None:
        registry = HistoricalAdapterRegistry()
        adapter = FormalDuckDBHistoricalDataAdapter()

        registry.register(adapter)

        self.assertIs(registry.get_adapter_for_format("duckdb"), adapter)
        self.assertTrue(registry.has_adapter("DUCKDB"))

    def test_registry_default_resolve_duckdb_pelo_adapter_formal(self) -> None:
        registry = create_default_historical_adapter_registry()

        adapter = registry.get_adapter_for_format("duckdb")

        self.assertIsInstance(adapter, FormalDuckDBHistoricalDataAdapter)

    def test_provider_resolve_duckdb_via_registry(self) -> None:
        provider = HistoricalDataProvider()

        adapter = provider.resolve_adapter("duckdb")

        self.assertIsInstance(adapter, FormalDuckDBHistoricalDataAdapter)

    def test_provider_nao_importa_adapter_duckdb_concreto(self) -> None:
        source = PROVIDER_PATH.read_text(encoding="utf-8")

        self.assertIn("HistoricalAdapterRegistry", source)
        self.assertNotIn("DuckDBHistoricalDataAdapter", source)

    def test_registry_default_registra_provider_duckdb(self) -> None:
        source = create_historical_data_source("duckdb")

        self.assertIsInstance(source, DuckDBHistoricalDataAdapter)

    def test_csv_permanece_provider_default(self) -> None:
        source = create_historical_data_source()

        self.assertEqual(type(source).__name__, "CsvHistoricalDataSource")

    def test_adapter_duckdb_carrega_candles_validos(self) -> None:
        result = DuckDBHistoricalDataAdapter().load(self._duckdb(2))

        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.candles), 2)
        self.assertEqual(result.candles[0].data, "2026-06-26 09:00")
        self.assertEqual(result.candles[1].fechamento, 101.0)

    def test_provider_carrega_historical_dataset_via_duckdb(self) -> None:
        provider = HistoricalDataProvider(
            data_source=DuckDBHistoricalDataAdapter(),
        )

        dataset = provider.load(
            self._duckdb(3),
            symbol="WDO",
            timeframe="1m",
        )

        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.total_candles, 3)
        self.assertEqual(dataset.start_date, "2026-06-26 09:00")
        self.assertEqual(dataset.end_date, "2026-06-26 09:02")

    def test_adapter_duckdb_aceita_tabela_configurada_por_origem_opaca(
        self,
    ) -> None:
        path = self._duckdb(2, table="wdo_candles")

        result = DuckDBHistoricalDataAdapter().load(
            {"database": path, "table": "wdo_candles"}
        )

        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.candles), 2)

    def test_adapter_duckdb_retorna_erro_controlado_para_estrutura_invalida(
        self,
    ) -> None:
        result = DuckDBHistoricalDataAdapter().load(
            self._duckdb_from_rows([{"foo": 1, "bar": 2}])
        )

        self.assertEqual(result.candles, [])
        self.assertIn("DuckDB com estrutura invalida.", result.errors)

    def test_leitura_duckdb_fica_isolada_no_adapter(self) -> None:
        files_with_duckdb_import = []
        for path in Path("market_data").glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "import duckdb" in source:
                files_with_duckdb_import.append(path.name)

        self.assertEqual(
            files_with_duckdb_import,
            ["duckdb_historical_data_adapter.py"],
        )

    def test_camadas_superiores_nao_importam_adapter_duckdb(self) -> None:
        forbidden_imports = {
            "market_data.duckdb_historical_data_adapter",
            "market_data.adapters.duckdb_historical_data_adapter",
            "DuckDBHistoricalDataAdapter",
        }
        for path in self._upper_layer_files():
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                source = path.read_text(encoding="utf-8")
                self.assertTrue(forbidden_imports.isdisjoint(imports))
                self.assertNotIn("DuckDBHistoricalDataAdapter", source)
                self.assertNotIn("duckdb", path.read_text(encoding="utf-8").lower())

    def test_adapter_formal_nao_acessa_operacao_real(self) -> None:
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

    def _duckdb(self, quantity: int, table: str = "candles") -> Path:
        rows = []
        for index in range(quantity):
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
        return self._duckdb_from_rows(rows, table=table)

    def _duckdb_from_rows(
        self,
        rows: list[dict[str, object]],
        table: str = "candles",
    ) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb")
        handle.close()
        path = Path(handle.name)
        path.unlink(missing_ok=True)
        frame = pd.DataFrame(rows)
        with duckdb.connect(str(path)) as connection:
            connection.execute(f"CREATE TABLE {table} AS SELECT * FROM frame")
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
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
                imports.add(node.module.split(".", 1)[0])
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
