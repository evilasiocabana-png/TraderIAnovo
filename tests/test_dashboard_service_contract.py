"""Contrato permanente entre dashboard_app.py e DashboardService."""

import ast
from pathlib import Path
import unittest
from unittest import mock

import application.dashboard_service as dashboard_service_module
from application.dashboard_service import DashboardService


class DashboardServiceContractTest(unittest.TestCase):
    """Protege a fachada consumida pelo dashboard visual."""

    DASHBOARD_PATH = Path("dashboard_app.py")

    def test_dashboard_service_implementa_todos_metodos_usados_pelo_dashboard(
        self,
    ) -> None:
        service = DashboardService()

        missing_methods = [
            method
            for method in self._dashboard_service_calls()
            if not callable(getattr(service, method, None))
        ]

        self.assertEqual(
            missing_methods,
            [],
            "DashboardService nao implementa:\n"
            + "\n".join(missing_methods),
        )

    def test_dashboard_nao_importa_infraestrutura_de_data_source(self) -> None:
        imports = self._dashboard_imports()
        source = self.DASHBOARD_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        forbidden_imports = {
            "HistoricalDataProvider",
            "HistoricalDatasetCatalog",
            "CsvHistoricalDataAdapter",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
            "pandas",
            "pathlib",
            "pathlib.Path",
            "csv",
            "market_data",
        }
        forbidden_calls = self._forbidden_calls(tree)

        self.assertTrue(
            forbidden_imports.isdisjoint(imports),
            f"dashboard_app.py importa infraestrutura proibida: "
            f"{sorted(forbidden_imports & imports)}",
        )
        self.assertEqual(
            forbidden_calls,
            [],
            "dashboard_app.py nao pode chamar open() diretamente.",
        )

    def test_dashboard_consumindo_apenas_dashboard_service_como_fachada(
        self,
    ) -> None:
        imports = self._dashboard_imports()

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("application.replay_service", imports)
        self.assertNotIn("application.research_lab_service", imports)
        self.assertNotIn("market_data.historical_dataset_catalog", imports)
        self.assertNotIn("market_data.historical_data_provider", imports)
        self.assertNotIn("market_data.historical_data_source_registry", imports)
        self.assertNotIn("replay.replay_engine", imports)
        self.assertNotIn("research.research_lab", imports)

    def test_dashboard_service_possui_contrato_minimo_obrigatorio(self) -> None:
        service = DashboardService()

        required_methods = [
            "list_historical_datasets",
            "get_historical_provider_metrics",
        ]

        for method in required_methods:
            with self.subTest(method=method):
                self.assertTrue(hasattr(service, method))
                self.assertTrue(callable(getattr(service, method)))

    def test_dashboard_service_instancia_sem_excecao(self) -> None:
        service = DashboardService()

        self.assertIsInstance(service, DashboardService)

    def test_dashboard_service_metodos_publicos_retornam_tipos_seguros(
        self,
    ) -> None:
        service = DashboardService()

        self.assertIsInstance(service.list_historical_datasets(), list)
        self.assertIsInstance(service.get_historical_provider_metrics(), dict)

    def test_mt5_import_falho_nao_quebra_dashboard(self) -> None:
        service = DashboardService()
        with mock.patch.object(dashboard_service_module, "_MT5_MODULE", None):
            with mock.patch.object(
                dashboard_service_module.importlib,
                "import_module",
                side_effect=NameError("name 'sys' is not defined"),
            ):
                history, status, message = service._load_mt5_trade_history()

        self.assertEqual(history, {})
        self.assertEqual(status, "INDISPONIVEL")
        self.assertIn("sys", message)

    def test_mt5_sonda_falha_nao_trava_historico(self) -> None:
        service = DashboardService()
        fake_result = mock.Mock(ok=False, message="Timeout na sonda MT5 initialize().")
        fake_mt5 = mock.Mock()

        with mock.patch.object(dashboard_service_module, "_MT5_MODULE", None):
            with mock.patch.object(
                dashboard_service_module.importlib,
                "import_module",
                return_value=fake_mt5,
            ):
                with mock.patch.object(
                    dashboard_service_module,
                    "probe_mt5_initialize",
                    return_value=fake_result,
                ):
                    history, status, message = service._load_mt5_trade_history()

        self.assertEqual(history, {})
        self.assertEqual(status, "OFFLINE")
        self.assertIn("Timeout", message)
        fake_mt5.initialize.assert_not_called()

    def _dashboard_service_calls(self) -> list[str]:
        tree = ast.parse(self.DASHBOARD_PATH.read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "service"
        }
        return sorted(calls)

    def _dashboard_imports(self) -> set[str]:
        tree = ast.parse(self.DASHBOARD_PATH.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                imports.update(alias.name for alias in node.names)
        return imports

    def _forbidden_calls(self, tree: ast.AST) -> list[str]:
        forbidden: list[str] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
            ):
                forbidden.append("open")
        return forbidden


if __name__ == "__main__":
    unittest.main()
