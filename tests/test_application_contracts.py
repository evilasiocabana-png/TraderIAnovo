"""Protecao de contratos entre servicos criticos da aplicacao."""

import importlib
from pathlib import Path
import unittest

from application.dashboard_service import DashboardService
from application.replay_service import ReplayService
from application.research_lab_service import ResearchLabService
from market_data import (
    CsvHistoricalDataSource,
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    ParquetHistoricalDataAdapter,
)
from tests.architecture_test_utils import calls_from, imports_from, python_files, read_source


class ApplicationContractsTest(unittest.TestCase):
    """Valida contratos arquiteturais entre application services."""

    UPPER_LAYER_FILES = (
        Path("application/dashboard_service.py"),
        Path("application/replay_service.py"),
        Path("application/research_lab_service.py"),
    )
    DASHBOARD_PATH = Path("dashboard_app.py")

    def test_servicos_criticos_instanciam_sem_excecao(self) -> None:
        services = [
            DashboardService(),
            ReplayService(),
            ResearchLabService(),
            HistoricalDataProvider(),
        ]

        self.assertIsInstance(services[0], DashboardService)
        self.assertIsInstance(services[1], ReplayService)
        self.assertIsInstance(services[2], ResearchLabService)
        self.assertIsInstance(services[3], HistoricalDataProvider)

    def test_imports_criticos_nao_quebram(self) -> None:
        modules = [
            "application.dashboard_service",
            "application.replay_service",
            "application.research_lab_service",
            "market_data",
            "market_data.historical_data_provider",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        ]

        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))

    def test_adapters_concretos_instanciam_sem_excecao(self) -> None:
        adapters = [
            CsvHistoricalDataSource(),
            ParquetHistoricalDataAdapter(),
            DuckDBHistoricalDataAdapter(),
        ]

        self.assertIsInstance(adapters[0], CsvHistoricalDataSource)
        self.assertIsInstance(adapters[1], ParquetHistoricalDataAdapter)
        self.assertIsInstance(adapters[2], DuckDBHistoricalDataAdapter)

    def test_dashboard_service_expoe_contratos_publicos_criticos(self) -> None:
        service = DashboardService()
        required_methods = [
            "get_dashboard_data",
            "load_demo_replay_candles",
            "start_replay",
            "stop_replay",
            "reset_replay",
            "next_replay_candle",
            "enable_replay_auto_run",
            "disable_replay_auto_run",
            "run_demo_research_experiment",
            "run_demo_research_benchmarks",
            "compare_research_benchmarks",
            "run_demo_parameter_grid",
            "validate_research_benchmarks",
            "clear_research_experiments",
            "list_historical_datasets",
            "select_historical_dataset",
            "get_selected_historical_dataset",
            "load_selected_historical_dataset_to_replay",
            "run_selected_historical_dataset_research_experiment",
            "analyze_selected_historical_dataset_quality",
            "list_historical_dataset_quality_validations",
            "get_historical_dataset_health_summary",
            "get_selected_historical_dataset_readiness",
            "list_data_readiness_gate_logs",
            "get_data_readiness_gate_metrics",
            "get_historical_provider_metrics",
            "save_configuration_preset",
            "load_configuration_preset",
            "list_configuration_presets",
            "delete_configuration_preset",
            "get_alpha001_status",
            "get_alpha001_paper_status",
        ]

        for method in required_methods:
            with self.subTest(method=method):
                self.assertTrue(hasattr(service, method))
                self.assertTrue(callable(getattr(service, method)))

    def test_dashboard_app_usa_dashboard_service_como_unica_fachada(self) -> None:
        imports = self._imports(self.DASHBOARD_PATH)

        self.assertIn("application.dashboard_service", imports)
        forbidden_modules = {
            "application.replay_service",
            "application.research_lab_service",
            "market_data",
            "market_data.historical_data_provider",
            "market_data.historical_dataset_catalog",
            "market_data.historical_data_source_registry",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "market_data.json_historical_dataset_quality_repository",
            "replay.replay_engine",
            "research.research_lab",
        }

        self.assertTrue(
            forbidden_modules.isdisjoint(imports),
            f"dashboard_app.py importa fachada proibida: "
            f"{sorted(forbidden_modules & imports)}",
        )

    def test_camadas_superiores_nao_importam_adapters_ou_formatos_fisicos(
        self,
    ) -> None:
        forbidden_imports = {
            "pandas",
            "duckdb",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "market_data.historical_data_source_registry",
        }

        for path in self.UPPER_LAYER_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} importa infraestrutura fisica: "
                    f"{sorted(forbidden_imports & imports)}",
                )

    def test_camadas_superiores_nao_chamam_leitura_fisica_de_data_source(
        self,
    ) -> None:
        forbidden_calls = {
            "read_csv",
            "read_parquet",
            "connect",
        }

        for path in self.UPPER_LAYER_FILES:
            with self.subTest(path=str(path)):
                calls = self._calls(path)
                self.assertTrue(
                    forbidden_calls.isdisjoint(calls),
                    f"{path} chama acesso fisico de Data Source: "
                    f"{sorted(forbidden_calls & calls)}",
                )

    def test_historical_data_provider_e_ponto_autorizado_para_datasets(
        self,
    ) -> None:
        imports = {
            path: self._imports(path)
            for path in (
                Path("application/replay_service.py"),
                Path("application/research_lab_service.py"),
            )
        }

        for path, module_imports in imports.items():
            with self.subTest(path=str(path)):
                self.assertIn("market_data", module_imports)
                source = read_source(path)
                self.assertIn("HistoricalDataProvider", source)
                self.assertNotIn("ParquetHistoricalDataAdapter", source)
                self.assertNotIn("DuckDBHistoricalDataAdapter", source)
                self.assertNotIn("CsvHistoricalDataSource", source)

    def test_adapters_sao_pontos_autorizados_para_formatos_fisicos(self) -> None:
        authorized = {
            Path("market_data/csv_historical_data_source.py"),
            Path("data/historical_data_loader.py"),
            Path("market_data/parquet_historical_data_adapter.py"),
            Path("market_data/duckdb_historical_data_adapter.py"),
        }
        forbidden_patterns = (
            "read_parquet",
            "duckdb.connect",
            "import duckdb",
            "import pandas",
        )

        for path in self._python_files():
            if path in authorized:
                continue
            text = read_source(path)
            leaked = [
                pattern
                for pattern in forbidden_patterns
                if pattern in text
            ]
            with self.subTest(path=str(path)):
                self.assertEqual(
                    leaked,
                    [],
                    f"{path} contem acesso fisico fora de adapter: {leaked}",
                )

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _calls(self, path: Path) -> set[str]:
        return calls_from(path)

    def _python_files(self) -> list[Path]:
        roots = [
            Path("application"),
            Path("dashboard_app.py"),
            Path("replay"),
            Path("research"),
            Path("market_data"),
            Path("data"),
        ]
        files: list[Path] = []
        for root in roots:
            if root.is_file():
                files.append(root)
                continue
            files.extend(python_files(root))
        return files


if __name__ == "__main__":
    unittest.main()
