"""Regras automaticas de dependencia entre camadas."""

import ast
from collections import defaultdict
from pathlib import Path
import unittest
from tests.architecture_test_utils import imports_from, parse_ast, python_files, read_source


class DependencyRulesTest(unittest.TestCase):
    """Protege Clean Architecture contra imports indevidos."""

    LAYERS = (
        "domain",
        "core",
        "application",
        "market",
        "replay",
        "research",
        "risk",
        "strategies",
        "database",
    )

    def test_domain_permanece_puro(self) -> None:
        forbidden_imports = {
            "application",
            "dashboard_app",
            "streamlit",
            "database",
            "infrastructure",
            "providers",
            "adapters",
            "broker",
            "mt5",
            "MetaTrader5",
            "market_data",
            "pandas",
            "pathlib",
            "csv",
            "duckdb",
        }
        forbidden_text = (
            "dashboard_app",
            "streamlit",
            ".csv",
            "parquet",
            "duckdb",
            "pandas",
            "Path(",
            "open(",
            "broker",
            "mt5",
            "MetaTrader5",
        )

        for path in self._python_files(Path("domain")):
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertEqual(
                    self._matches(imports, forbidden_imports),
                    set(),
                    f"{path} importou dependencia proibida",
                )
                source = read_source(path)
                leaked = [term for term in forbidden_text if term in source]
                self.assertEqual(leaked, [], f"{path} violou pureza do dominio")

    def test_strategies_nao_importam_execucao_ui_ou_risco_direto(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "application.dashboard_service",
            "risk.risk_engine",
            "core.order_manager",
        }

        self._assert_layer_forbidden_imports("strategies", forbidden)

    def test_application_nao_importa_ui_broker_real_ou_corretora(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
            "corretora",
        }

        self._assert_layer_forbidden_imports("application", forbidden)

    def test_market_nao_importa_ui_ou_dashboard_service(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "application.dashboard_service",
        }

        self._assert_layer_forbidden_imports("market", forbidden)

    def test_risk_nao_importa_ui_ou_dashboard_service(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "application.dashboard_service",
        }

        self._assert_layer_forbidden_imports("risk", forbidden)

    def test_replay_nao_importa_ui_broker_real_ou_mt5(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
        }

        self._assert_layer_forbidden_imports("replay", forbidden)

    def test_research_nao_importa_ui_broker_real_ou_mt5(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "core.broker",
            "broker",
            "mt5",
            "MetaTrader5",
        }

        self._assert_layer_forbidden_imports("research", forbidden)

    def test_dashboard_app_permanece_apenas_camada_de_apresentacao(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))
        forbidden = {
            "database",
            "sqlite3",
            "strategies",
            "replay",
            "replay.replay_engine",
            "research",
            "research.research_lab",
            "market_data",
            "market_data.historical_data_provider",
            "market_data.historical_dataset_catalog",
            "market_data.historical_data_source_registry",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
            "pandas",
            "pathlib",
            "csv",
            "duckdb",
        }
        source = read_source(Path("dashboard_app.py"))
        tree = parse_ast(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertEqual(
            self._matches(imports, forbidden),
            set(),
            "dashboard_app.py importou dependencia proibida",
        )
        self.assertNotIn("open(", source)
        self.assertFalse(self._calls_named(tree, {"read_csv", "read_parquet"}))

    def test_nao_ha_ciclos_proibidos_com_domain_database_ou_ui(self) -> None:
        graph = self._layer_graph()
        cycles = self._two_node_cycles(graph)
        protected_layers = {"domain", "database"}
        prohibited = [
            cycle
            for cycle in cycles
            if protected_layers.intersection(cycle)
        ]

        self.assertEqual(
            prohibited,
            [],
            "Ciclo proibido envolvendo dominio ou infraestrutura: "
            + str(prohibited),
        )

    def _assert_layer_forbidden_imports(
        self,
        layer: str,
        forbidden: set[str],
    ) -> None:
        for path in self._python_files(Path(layer)):
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertEqual(
                    self._matches(imports, forbidden),
                    set(),
                    f"{path} importou dependencia proibida",
                )

    def _python_files(self, root: Path) -> list[Path]:
        return python_files(root)

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _matches(self, imports: set[str], forbidden: set[str]) -> set[str]:
        matches: set[str] = set()
        for imported in imports:
            root = imported.split(".", maxsplit=1)[0]
            if imported in forbidden or root in forbidden:
                matches.add(imported)
        return matches

    def _calls_named(self, tree: ast.AST, names: set[str]) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in names:
                    return True
                if isinstance(node.func, ast.Attribute) and node.func.attr in names:
                    return True
        return False

    def _layer_graph(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = defaultdict(set)
        for layer in self.LAYERS:
            for path in self._python_files(Path(layer)):
                for imported in self._imports(path):
                    root = imported.split(".", maxsplit=1)[0]
                    if root in self.LAYERS and root != layer:
                        graph[layer].add(root)
        return graph

    def _two_node_cycles(
        self,
        graph: dict[str, set[str]],
    ) -> list[tuple[str, str]]:
        cycles: list[tuple[str, str]] = []
        for origin, targets in graph.items():
            for target in targets:
                if origin in graph.get(target, set()):
                    cycle = tuple(sorted((origin, target)))
                    if cycle not in cycles:
                        cycles.append(cycle)
        return sorted(cycles)


if __name__ == "__main__":
    unittest.main()
