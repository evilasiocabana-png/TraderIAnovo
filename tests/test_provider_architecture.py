"""Protecao arquitetural de providers e adapters historicos."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
import unittest

from domain.candle import Candle
from market_data import (
    CsvHistoricalDataSource,
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    HistoricalDataSourceRegistry,
    HistoricalDataSourceResult,
    HistoricalDatasetCatalog,
    ParquetHistoricalDataAdapter,
    create_historical_data_source,
)
from tests.architecture_test_utils import (
    calls_from,
    collect_forbidden_text_violations,
    files_from_roots,
    imports_from,
    parse_ast,
    python_files,
    read_source,
)


class ProviderArchitectureTest(unittest.TestCase):
    """Garante separacao entre provider autorizado e adapters fisicos."""

    HISTORICAL_ADAPTER_FILES = {
        Path("market_data/csv_historical_data_source.py"),
        Path("market_data/parquet_historical_data_adapter.py"),
        Path("market_data/duckdb_historical_data_adapter.py"),
        Path("data/historical_data_loader.py"),
    }
    UPPER_LAYER_FILES = (
        Path("application/dashboard_service.py"),
        Path("application/replay_service.py"),
        Path("application/research_lab_service.py"),
        Path("dashboard_app.py"),
        Path("replay/replay_engine.py"),
        Path("research/research_lab.py"),
        Path("research/strategy_benchmark.py"),
    )

    def test_componentes_de_provider_importam_e_instanciam_sem_excecao(self) -> None:
        modules = [
            "market_data.historical_data_provider",
            "market_data.historical_dataset_catalog",
            "market_data.historical_data_source_registry",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        ]

        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))

        self.assertIsInstance(HistoricalDataProvider(), HistoricalDataProvider)
        self.assertIsInstance(HistoricalDatasetCatalog(), HistoricalDatasetCatalog)
        self.assertIsInstance(HistoricalDataSourceRegistry(), HistoricalDataSourceRegistry)
        self.assertIsInstance(CsvHistoricalDataSource(), CsvHistoricalDataSource)
        self.assertIsInstance(
            ParquetHistoricalDataAdapter(),
            ParquetHistoricalDataAdapter,
        )
        self.assertIsInstance(
            DuckDBHistoricalDataAdapter(),
            DuckDBHistoricalDataAdapter,
        )

    def test_registry_mantem_csv_default_e_resolve_adapters_por_nome(self) -> None:
        registry = HistoricalDataSourceRegistry()
        registry.register("csv", CsvHistoricalDataSource)
        registry.register("parquet", ParquetHistoricalDataAdapter)
        registry.register("duckdb", DuckDBHistoricalDataAdapter)

        self.assertIsInstance(create_historical_data_source(), CsvHistoricalDataSource)
        self.assertIsInstance(registry.create("CSV"), CsvHistoricalDataSource)
        self.assertIsInstance(registry.create("PARQUET"), ParquetHistoricalDataAdapter)
        self.assertIsInstance(registry.create("DUCKDB"), DuckDBHistoricalDataAdapter)
        self.assertEqual(registry.names(), ["csv", "duckdb", "parquet"])

    def test_historical_data_provider_e_fachada_autorizada_para_datasets(self) -> None:
        provider = HistoricalDataProvider(data_source=_FakeHistoricalDataSource())

        dataset = provider.load("origem-opaca", symbol="WDO", timeframe="1m")

        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.total_candles, 1)
        self.assertEqual(provider.loaded_datasets, [dataset])
        self.assertEqual(provider.errors, [])

    def test_servicos_de_aplicacao_nao_importam_adapters_concretos(self) -> None:
        forbidden_imports = {
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
        }

        for path in self.UPPER_LAYER_FILES:
            with self.subTest(path=str(path)):
                imports = imports_from(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} conhece adapter concreto: "
                    f"{sorted(forbidden_imports & imports)}",
                )

    def test_replay_e_research_usam_provider_autorizado_para_historicos(self) -> None:
        replay_source = read_source(Path("application/replay_service.py"))
        research_source = read_source(Path("application/research_lab_service.py"))

        self.assertIn("HistoricalDataProvider", replay_source)
        self.assertIn("MarketDataProvider", replay_source)
        self.assertIn("self.market_data_provider.load", replay_source)
        self.assertIn("HistoricalDataProvider", research_source)
        self.assertIn("MarketDataProvider", research_source)
        self.assertIn("self.market_data_provider.load", research_source)

    def test_dashboard_nao_acessa_market_data_ou_adapters_diretamente(self) -> None:
        imports = imports_from(Path("dashboard_app.py"))
        forbidden = {
            "market_data",
            "market_data.historical_data_provider",
            "market_data.historical_dataset_catalog",
            "market_data.historical_data_source_registry",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }

        self.assertTrue(
            forbidden.isdisjoint(imports),
            f"dashboard_app.py acessa Market Data diretamente: "
            f"{sorted(forbidden & imports)}",
        )

    def test_catalogo_nao_executa_leitura_fisica_pesada(self) -> None:
        path = Path("market_data/historical_dataset_catalog.py")
        imports = imports_from(path)
        calls = calls_from(path)
        source = read_source(path)

        self.assertTrue({"pandas", "duckdb", "pathlib", "csv"}.isdisjoint(imports))
        self.assertTrue(
            {"open", "read_csv", "read_parquet", "connect", "glob", "iterdir"}.isdisjoint(calls)
        )
        self.assertNotIn(".csv", source)
        self.assertNotIn(".parquet", source)

    def test_registry_apenas_registra_e_resolve_adapters(self) -> None:
        path = Path("market_data/historical_data_source_registry.py")
        imports = imports_from(path)
        calls = calls_from(path)

        self.assertTrue(
            {
                "dashboard_app",
                "application.dashboard_service",
                "application.replay_service",
                "application.research_lab_service",
                "pandas",
                "duckdb",
                "pathlib",
                "csv",
            }.isdisjoint(imports)
        )
        self.assertTrue(
            {"open", "read_csv", "read_parquet", "connect"}.isdisjoint(calls)
        )
        self.assertIn("register", self._public_methods(path, "HistoricalDataSourceRegistry"))
        self.assertIn("create", self._public_methods(path, "HistoricalDataSourceRegistry"))
        self.assertIn("names", self._public_methods(path, "HistoricalDataSourceRegistry"))

    def test_acesso_fisico_historico_fica_restrito_a_adapters_autorizados(self) -> None:
        forbidden_patterns = (
            "read_csv",
            "read_parquet",
            "import pandas",
            "import duckdb",
            "duckdb.connect",
            ".parquet\"",
            ".parquet'",
            "load_csv(",
        )
        violations = collect_forbidden_text_violations(
            self._production_python_files(),
            forbidden_patterns,
            authorized_paths=(
                self.HISTORICAL_ADAPTER_FILES
                | {Path("application/research_lab_service.py")}
            ),
        )

        self.assertEqual(
            violations,
            [],
            "Acesso fisico historico fora de adapter autorizado: "
            + "; ".join(str(violation) for violation in violations),
        )

    def test_camadas_superiores_nao_chamam_leitura_fisica_de_historicos(self) -> None:
        forbidden_calls = {
            "read_csv",
            "read_parquet",
            "connect",
            "glob",
            "iterdir",
            "listdir",
            "load_csv",
        }

        for path in self.UPPER_LAYER_FILES:
            if path == Path("application/research_lab_service.py"):
                forbidden_for_path = forbidden_calls - {"open"}
            else:
                forbidden_for_path = forbidden_calls | {"open"}
            with self.subTest(path=str(path)):
                calls = calls_from(path)
                self.assertTrue(
                    forbidden_for_path.isdisjoint(calls),
                    f"{path} chama leitura fisica proibida: "
                    f"{sorted(forbidden_for_path & calls)}",
                )

    def test_domain_permanece_puro_sem_provider_adapter_ou_arquivo_fisico(self) -> None:
        forbidden_imports = {
            "market_data",
            "providers",
            "adapters",
            "pandas",
            "duckdb",
            "pathlib",
            "csv",
        }
        forbidden_text = (
            "HistoricalDataProvider",
            "HistoricalDatasetCatalog",
            "HistoricalDataSourceRegistry",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
            ".csv",
            ".parquet",
            "open(",
            "Path(",
        )

        for path in python_files(Path("domain")):
            with self.subTest(path=str(path)):
                imports = imports_from(path)
                source = read_source(path)
                self.assertTrue(forbidden_imports.isdisjoint(imports))
                self.assertEqual(
                    [pattern for pattern in forbidden_text if pattern in source],
                    [],
                )

    def test_adapters_fisicos_implementam_a_mesma_porta(self) -> None:
        for adapter in (
            CsvHistoricalDataSource(),
            ParquetHistoricalDataAdapter(),
            DuckDBHistoricalDataAdapter(),
        ):
            with self.subTest(adapter=adapter.__class__.__name__):
                self.assertTrue(callable(getattr(adapter, "load", None)))

    def _public_methods(self, path: Path, class_name: str) -> set[str]:
        for node in ast.walk(parse_ast(path)):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return {
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                    and not item.name.startswith("_")
                }
        return set()

    def _production_python_files(self) -> list[Path]:
        roots = (
            Path("application"),
            Path("dashboard_app.py"),
            Path("data"),
            Path("domain"),
            Path("market_data"),
            Path("replay"),
            Path("research"),
        )
        return files_from_roots(roots)


class _FakeHistoricalDataSource:
    """Fonte fake para validar o provider sem arquivo fisico."""

    def load(self, source: object) -> HistoricalDataSourceResult:
        return HistoricalDataSourceResult(
            candles=[
                Candle(
                    data="2026-06-26 09:00",
                    abertura=100.0,
                    maxima=105.0,
                    minima=95.0,
                    fechamento=102.0,
                    volume=1000,
                )
            ],
            errors=[],
        )


if __name__ == "__main__":
    unittest.main()
