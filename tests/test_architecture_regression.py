"""Suite consolidada de regressao arquitetural."""

from __future__ import annotations

import importlib
from pathlib import Path
import unittest

from tests.architecture_test_utils import (
    collect_forbidden_text_violations,
    calls_from,
    files_from_roots,
    forbidden_text_in,
    imported_roots,
    imports_from,
    python_files,
    read_source,
)


class ArchitectureRegressionTest(unittest.TestCase):
    """Revalida fronteiras criticas protegidas nas sprints CTO."""

    LAYERS = (
        "application",
        "core",
        "domain",
        "market",
        "market_data",
        "replay",
        "research",
        "risk",
        "strategies",
    )
    AUTHORIZED_HISTORICAL_FORMAT_FILES = {
        Path("market_data/csv_historical_data_source.py"),
        Path("market_data/parquet_historical_data_adapter.py"),
        Path("market_data/duckdb_historical_data_adapter.py"),
        Path("data/historical_data_loader.py"),
    }
    APPLICATION_EXPORT_EXCEPTIONS = {
        Path("application/research_lab_service.py"),
    }

    def test_imports_criticos_permanecem_validos(self) -> None:
        imports = [
            "application.dashboard_service",
            "application.replay_service",
            "application.research_lab_service",
            "application.configuration_service",
            "application.session_service",
            "core.event_bus",
            "domain.contracts.strategy_signal",
            "domain.contracts.market_snapshot",
            "domain.contracts.risk_decision",
            "domain.contracts.decision_context",
            "domain.contracts.execution_order",
            "domain.contracts.backtest_result",
            "market_data.historical_data_provider",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "replay.replay_engine",
            "research.research_lab",
        ]

        for module_name in imports:
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_dashboard_service_permanece_fachada_unica_da_ui(self) -> None:
        imports = imports_from(Path("dashboard_app.py"))
        allowed = {
            "date",
            "datetime",
            "inspect",
            "os",
            "time",
            "streamlit",
            "application.dashboard_service",
            "application.dashboard_view_model",
            "DASHBOARD_VIEW_MODEL_CONTRACT_VERSION",
            "DashboardService",
        }
        forbidden = {
            "application.replay_service",
            "ReplayService",
            "application.research_lab_service",
            "ResearchLabService",
            "application.configuration_service",
            "ConfigurationService",
            "application.session_service",
            "SessionService",
            "market_data",
            "database",
            "strategies",
            "replay",
            "research",
            "core",
            "market",
            "risk",
        }

        self.assertIn("application.dashboard_service", imports)
        self.assertTrue(imports.issubset(allowed))
        self.assertTrue(forbidden.isdisjoint(imports))

    def test_dashboard_nao_acessa_persistencia_ou_formatos_fisicos(self) -> None:
        path = Path("dashboard_app.py")
        calls = calls_from(path)
        source = read_source(path)
        forbidden_calls = {
            "open",
            "Path",
            "read_csv",
            "read_parquet",
            "connect",
            "to_csv",
            "glob",
            "iterdir",
            "listdir",
        }
        forbidden_text = (
            "import pandas",
            "import duckdb",
            "sqlite3",
            "HistoricalDataProvider",
            "HistoricalDatasetCatalog",
            "ConfigurationManager",
            "SessionManager",
            "EventBus",
            "ReplayService(",
            "ResearchLabService(",
            "ResearchLab(",
        )

        self.assertTrue(forbidden_calls.isdisjoint(calls))
        leaked = [fragment for fragment in forbidden_text if fragment in source]
        self.assertEqual(leaked, [])

    def test_domain_permanece_puro(self) -> None:
        forbidden_import_roots = {
            "application",
            "dashboard_app",
            "streamlit",
            "database",
            "market_data",
            "providers",
            "adapters",
            "pandas",
            "duckdb",
            "pathlib",
            "csv",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_text = (
            ".csv",
            ".parquet",
            "open(",
            "Path(",
            "HistoricalDataProvider",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
        )

        for path in python_files(Path("domain")):
            with self.subTest(path=str(path)):
                roots = imported_roots(path)
                self.assertTrue(forbidden_import_roots.isdisjoint(roots))
                self.assertEqual(forbidden_text_in(path, forbidden_text), [])

    def test_application_nao_depende_de_ui_ou_adapters_fisicos(self) -> None:
        forbidden_imports = {
            "dashboard_app",
            "streamlit",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "pandas",
            "duckdb",
            "broker",
            "mt5",
            "MetaTrader5",
        }

        for path in python_files(Path("application")):
            with self.subTest(path=str(path)):
                imports = imports_from(path)
                self.assertTrue(forbidden_imports.isdisjoint(imports))

    def test_strategies_nao_executam_ordens_reais(self) -> None:
        forbidden_imports = {
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
            "application.dashboard_service",
            "streamlit",
        }
        forbidden_calls = {
            "order_send",
            "send_order",
            "place_order",
            "execute_order",
            "executar_ordem",
            "enviar_ordem",
        }

        for path in python_files(Path("strategies")):
            with self.subTest(path=str(path)):
                self.assertTrue(forbidden_imports.isdisjoint(imports_from(path)))
                self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def test_replay_nao_acessa_ui_corretora_mt5_ou_infra_fisica(self) -> None:
        forbidden_imports = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
            "pandas",
            "duckdb",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }
        forbidden_calls = {
            "open",
            "read_csv",
            "read_parquet",
            "connect",
            "order_send",
            "send_order",
            "execute_order",
        }

        for path in [
            *python_files(Path("replay")),
            Path("application/replay_service.py"),
        ]:
            with self.subTest(path=str(path)):
                self.assertTrue(forbidden_imports.isdisjoint(imports_from(path)))
                self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def test_research_nao_acessa_ui_corretora_mt5_ou_execucao_real(self) -> None:
        forbidden_imports = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
            "pandas",
            "duckdb",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }
        forbidden_calls = {
            "order_send",
            "send_order",
            "place_order",
            "execute_order",
            "executar_ordem",
            "enviar_ordem",
        }

        for path in [
            *python_files(Path("research")),
            Path("application/research_lab_service.py"),
        ]:
            with self.subTest(path=str(path)):
                self.assertTrue(forbidden_imports.isdisjoint(imports_from(path)))
                self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def test_apenas_adapters_autorizados_acessam_formatos_historicos(self) -> None:
        forbidden_patterns = (
            "read_csv",
            "read_parquet",
            "import pandas",
            "import duckdb",
            "duckdb.connect",
            "load_csv(",
            ".parquet\"",
            ".parquet'",
        )
        violations = collect_forbidden_text_violations(
            self._production_python_files(),
            forbidden_patterns,
            authorized_paths=(
                self.AUTHORIZED_HISTORICAL_FORMAT_FILES
                | self.APPLICATION_EXPORT_EXCEPTIONS
            ),
        )

        self.assertEqual(
            violations,
            [],
            "Acesso fisico historico fora de adapter autorizado: "
            + "; ".join(str(violation) for violation in violations),
        )

    def test_historical_data_provider_continua_fachada_autorizada(self) -> None:
        replay_source = read_source(Path("application/replay_service.py"))
        research_source = read_source(Path("application/research_lab_service.py"))
        provider_source = read_source(Path("market_data/historical_data_provider.py"))

        self.assertIn("HistoricalDataProvider", replay_source)
        self.assertIn("self.market_data_provider.load", replay_source)
        self.assertIn("HistoricalDataProvider", research_source)
        self.assertIn("self.market_data_provider.load", research_source)
        self.assertIn("class HistoricalDataProvider", provider_source)
        self.assertIn("data_source: HistoricalDataSource", provider_source)

    def test_event_bus_permanece_mecanismo_oficial_de_eventos(self) -> None:
        event_bus_source = read_source(Path("core/event_bus.py"))
        events_source = read_source(Path("core/events.py"))
        replay_source = read_source(Path("application/replay_service.py"))
        replay_engine_source = read_source(Path("replay/replay_engine.py"))

        self.assertIn("class EventBus", event_bus_source)
        self.assertIn("OFFICIAL_EVENTS", events_source)
        self.assertIn("self.event_bus.publish", replay_source)
        self.assertIn("self.event_bus.publish", replay_engine_source)
        self.assertNotIn("SessionManager", replay_source)

    def test_modulos_superiores_nao_acessam_persistencia_fisica_diretamente(
        self,
    ) -> None:
        forbidden_calls = {
            "read_csv",
            "read_parquet",
            "connect",
            "glob",
            "iterdir",
            "listdir",
        }
        upper_paths = [
            Path("dashboard_app.py"),
            *python_files(Path("application")),
            *python_files(Path("replay")),
            *python_files(Path("research")),
        ]

        for path in upper_paths:
            if path in self.APPLICATION_EXPORT_EXCEPTIONS:
                continue
            with self.subTest(path=str(path)):
                self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def test_segurança_operacional_sem_ordem_real_autorizada(self) -> None:
        forbidden_patterns = (
            "mt5.order_send",
            "order_send(",
            "send_order(",
            "place_order(",
            "execute_order(",
            "real_trading_authorized=True",
        )
        scan_roots = (
            Path("application"),
            Path("core"),
            Path("replay"),
            Path("research"),
            Path("risk"),
            Path("strategies"),
            Path("dashboard_app.py"),
        )
        violations = collect_forbidden_text_violations(
            files_from_roots(scan_roots),
            forbidden_patterns,
        )

        self.assertEqual(violations, [])
        broker_source = read_source(Path("core/broker.py"))
        self.assertIn("class SimulatedBroker", broker_source)
        self.assertNotIn("MetaTrader5", broker_source)
        self.assertNotIn("mt5", broker_source)

    def _production_python_files(self) -> list[Path]:
        roots = (
            Path("application"),
            Path("dashboard_app.py"),
            Path("data"),
            Path("domain"),
            Path("market_data"),
            Path("replay"),
            Path("research"),
            Path("strategies"),
        )
        return files_from_roots(roots)


if __name__ == "__main__":
    unittest.main()
