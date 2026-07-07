"""Protecao da fachada unica entre dashboard_app.py e application."""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
import unittest

from application.dashboard_service import DashboardData, DashboardService
from tests.architecture_test_utils import (
    attributes_from,
    calls_from,
    imports_from,
    parse_ast,
    read_source,
)


class DashboardFacadeTest(unittest.TestCase):
    """Congela DashboardService como unica fachada consumida pela UI."""

    DASHBOARD_PATH = Path("dashboard_app.py")
    ALLOWED_IMPORTS = {
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
    FORBIDDEN_IMPORTS = {
        "application.replay_service",
        "ReplayService",
        "application.research_lab_service",
        "ResearchLabService",
        "application.configuration_service",
        "ConfigurationService",
        "application.session_service",
        "SessionService",
        "core",
        "core.event_bus",
        "EventBus",
        "core.configuration_manager",
        "ConfigurationManager",
        "core.operation_session",
        "OperationSession",
        "core.session_manager",
        "SessionManager",
        "market_data",
        "HistoricalDataProvider",
        "HistoricalDatasetCatalog",
        "HistoricalDataSourceRegistry",
        "CsvHistoricalDataSource",
        "ParquetHistoricalDataAdapter",
        "DuckDBHistoricalDataAdapter",
        "database",
        "sqlite3",
        "persistence",
        "providers",
        "adapters",
        "strategies",
        "replay",
        "replay.replay_engine",
        "research",
        "research.research_lab",
        "market",
        "risk",
        "pandas",
        "duckdb",
        "pathlib",
        "Path",
        "csv",
    }
    FORBIDDEN_DIRECT_CALLS = {
        "ReplayService",
        "ResearchLabService",
        "ResearchLab",
        "ConfigurationService",
        "SessionService",
        "ConfigurationManager",
        "SessionManager",
        "OperationSession",
        "EventBus",
        "HistoricalDataProvider",
        "HistoricalDatasetCatalog",
        "HistoricalDataSourceRegistry",
        "CsvHistoricalDataSource",
        "ParquetHistoricalDataAdapter",
        "DuckDBHistoricalDataAdapter",
        "Path",
        "open",
        "read_csv",
        "read_parquet",
        "connect",
    }
    REQUIRED_DASHBOARD_DATA_FIELDS = {
        "system_status",
        "market_snapshot",
        "strategy_signal",
        "regime_data",
        "research_data",
        "replay_data",
        "research_lab_experiments",
        "last_research_experiment",
        "research_benchmarks",
        "benchmark_comparison",
        "parameter_grid_results",
        "best_parameter_grid_result",
        "benchmark_validations",
        "last_benchmark_validation",
        "configuration_data",
        "session_snapshot",
        "alpha001_status",
        "alpha001_research_report",
        "alpha001_dashboard_research",
        "research_report",
        "mt5_market_data",
        "mt5_forex_signals",
        "timeframe_optimizer",
    }
    REQUIRED_WORKBENCH_SECTIONS = {
        "MT5 Forex",
        "Laboratorio de Pesquisa",
        "Historico MT5",
        "Relatorios",
        "Sistema Forex",
        "Robo Demo MT5",
        "Entrada Teorica MT5",
        "Calibracao Forex MT5",
        "Historico MT5 Forex",
    }

    def test_dashboard_importa_apenas_fachada_dashboard_service(self) -> None:
        imports = self._imports()

        self.assertIn("application.dashboard_service", imports)
        self.assertIn("DashboardService", imports)
        self.assertTrue(
            imports.issubset(self.ALLOWED_IMPORTS),
            f"dashboard_app.py importou modulo fora da camada de apresentacao: "
            f"{sorted(imports - self.ALLOWED_IMPORTS)}",
        )
        self.assertTrue(
            self.FORBIDDEN_IMPORTS.isdisjoint(imports),
            f"dashboard_app.py importou dependencia proibida: "
            f"{sorted(self.FORBIDDEN_IMPORTS & imports)}",
        )

    def test_dashboard_nao_instancia_servicos_internos_ou_infraestrutura(self) -> None:
        calls = self._call_names()
        forbidden = self.FORBIDDEN_DIRECT_CALLS - {"open"}

        self.assertTrue(
            forbidden.isdisjoint(calls),
            f"dashboard_app.py instancia/chama dependencia proibida: "
            f"{sorted(forbidden & calls)}",
        )
        self.assertIn("DashboardService", calls)

    def test_dashboard_nao_acessa_arquivos_persistencia_ou_dataframes(self) -> None:
        calls = self._call_names()
        attributes = self._attribute_names()
        source = read_source(self.DASHBOARD_PATH)

        forbidden_calls = {
            "open",
            "read_csv",
            "read_parquet",
            "to_csv",
            "connect",
            "execute",
            "fetchall",
            "glob",
            "iterdir",
            "listdir",
        }
        forbidden_attributes = {
            "read_csv",
            "read_parquet",
            "connect",
            "to_sql",
            "to_parquet",
        }

        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertTrue(forbidden_attributes.isdisjoint(attributes))
        self.assertNotIn("import pandas", source)
        self.assertNotIn("import duckdb", source)
        self.assertNotIn("pathlib", source)
        self.assertNotIn("sqlite3", source)

    def test_todos_metodos_service_usados_pela_ui_existem_na_fachada(self) -> None:
        service = DashboardService()
        missing_or_not_callable = [
            method
            for method in self._service_method_calls()
            if not callable(getattr(service, method, None))
        ]

        self.assertEqual(
            missing_or_not_callable,
            [],
            "DashboardService nao implementa metodos usados pela UI: "
            + ", ".join(missing_or_not_callable),
        )

    def test_dashboard_service_expoe_dados_para_abas_principais(self) -> None:
        data = DashboardService().get_dashboard_data()
        field_names = {field.name for field in fields(DashboardData)}

        self.assertTrue(self.REQUIRED_DASHBOARD_DATA_FIELDS.issubset(field_names))
        self.assertIsNotNone(data.system_status)
        self.assertIsNotNone(data.replay_data)
        self.assertIsInstance(data.research_lab_experiments, list)
        self.assertIsInstance(data.research_benchmarks, list)
        self.assertIsNotNone(data.configuration_data)
        self.assertIsNotNone(data.session_snapshot)

    def test_dashboard_app_renderiza_workbench_unico_por_fachada(self) -> None:
        source = read_source(self.DASHBOARD_PATH)

        self.assertIn("st.tabs", source)
        for section in self.REQUIRED_WORKBENCH_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(f'"{section}"', source)
        self.assertNotIn("infrastructure.market_data", source)
        for renderer in (
            "exibir_dashboard_layout(service, data)",
            "exibir_mt5_forex_dashboard(service, data)",
            "exibir_research_dashboard(service, data)",
            "exibir_mt5_history_comparison_dashboard(service, data)",
            "exibir_relatorios_dashboard(service, data)",
            "exibir_sistema_dashboard(data)",
        ):
            with self.subTest(renderer=renderer):
                self.assertIn(renderer, source)

    def test_replay_research_sistema_configuracao_sessao_usam_fachada(self) -> None:
        service_calls = set(self._dashboard_service_facade_calls())
        expected_calls = {
            "load_selected_historical_dataset_to_replay",
            "start_replay",
            "next_replay_candle",
            "stop_replay",
            "reset_replay",
            "enable_replay_auto_run",
            "disable_replay_auto_run",
            "run_selected_historical_dataset_research_experiment",
            "update_configuration",
            "save_configuration_preset",
            "load_configuration_preset",
            "list_configuration_presets",
            "delete_configuration_preset",
            "get_dashboard_data",
            "load_mt5_forex_signals",
            "load_mt5_market_data",
        }

        self.assertTrue(
            expected_calls.issubset(service_calls),
            f"Chamadas esperadas via DashboardService ausentes: "
            f"{sorted(expected_calls - service_calls)}",
        )

    def test_dashboard_nao_contem_regras_operacionais_de_ordem_ou_risco(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        forbidden_fragments = {
            "order_send(",
            "mt5.order_send",
            "send_order",
            "place_order",
            "execute_order",
            "executar_ordem",
            "enviar_ordem",
            "RiskEngine(",
            "DecisionPipeline(",
            "StrategyFactory(",
            "ReplayService(",
            "ResearchLabService(",
            "ResearchLab(",
        }

        leaked = [
            fragment
            for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_dashboard_nao_calcula_ranking_do_timeframe_optimizer(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        forbidden_fragments = {
            "TimeframeOptimizer(",
            "TimeframeCandidate(",
            "TimeframeOptimizerConfiguration(",
            "_rank_score",
            "profit_factor_score",
            "drawdown_score",
        }

        leaked = [
            fragment
            for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_dashboard_exibe_mt5_forex_heuristico_simples(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        required_fragments = {
            '"Status"',
            '"Timeframe"',
            '"Ultimo preco"',
            '"Horario"',
            '"Tendencia"',
            '"Momentum"',
            '"Volatilidade"',
            '"RSI"',
            '"Media curta"',
            '"Media longa"',
            '"Decisao"',
            '"Confianca"',
            '"Candles recebidos"',
            '"Ultima atualizacao"',
            '"Motivo"',
        }

        missing = [
            fragment
            for fragment in required_fragments
            if fragment not in source
        ]

        self.assertEqual(missing, [])

    def test_mt5_forex_nao_possui_input_ou_count_para_candles(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        tree = parse_ast(self.DASHBOARD_PATH)
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        forex_function = functions["exibir_mt5_forex_dashboard"]
        function_source = ast.get_source_segment(source, forex_function) or ""

        self.assertNotIn("mt5_forex_candles", function_source)
        self.assertNotIn("number_input", function_source)
        self.assertNotIn("count=", function_source)
        self.assertIn("load_mt5_forex_signals", function_source)
        self.assertIn("Candles por par", function_source)

    def test_mt5_forex_refresh_nao_expoe_research_pesado(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        tree = parse_ast(self.DASHBOARD_PATH)
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        function_source = ast.get_source_segment(
            source,
            functions["exibir_mt5_forex_dashboard"],
        ) or ""

        self.assertNotIn('"Aplicar timeframe"', function_source)
        self.assertIn("load_mt5_forex_signals", function_source)
        self.assertNotIn('"Recalcular Research"', function_source)
        self.assertNotIn("recalculate_mt5_research", function_source)
        self.assertNotIn("load_timeframe_optimization_results", function_source)

    def test_mt5_forex_nao_expoe_diagnostico_pesado_na_tela_principal(self) -> None:
        source = read_source(self.DASHBOARD_PATH)
        tree = parse_ast(self.DASHBOARD_PATH)
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        function_source = ast.get_source_segment(
            source,
            functions["exibir_mt5_forex_dashboard"],
        ) or ""

        self.assertNotIn("test_mt5_connection", function_source)
        self.assertNotIn("_exibir_mt5_connection_diagnostic", function_source)
        self.assertNotIn("MetaTrader5", function_source)

    def test_mt5_safe_mode_exibe_diagnostico_minimo(self) -> None:
        source = read_source(self.DASHBOARD_PATH)

        self.assertIn("MT5 Safe Mode", source)
        self.assertIn("Safe Mode", source)
        self.assertIn("ATIVO", source)
        self.assertIn("MT5_SAFE_MODE", source)
        self.assertIn("Ultima atualizacao", source)
        self.assertIn("Refresh ID", source)
        self.assertIn("Ultima vela recebida", source)
        self.assertIn("Candles recebidos", source)
        self.assertIn("Ultimo preco", source)
        self.assertIn("Diagnostico MT5", source)
        self.assertIn("Erro MT5", source)

    def test_dashboard_service_research_pesado_desconectado_do_mt5_forex(self) -> None:
        source = read_source(Path("application/dashboard_service.py"))
        tree = parse_ast(Path("application/dashboard_service.py"))
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        function_source = ast.get_source_segment(
            source,
            functions["recalculate_mt5_research"],
        ) or ""

        self.assertIn("run_mt5_research_calibration", function_source)
        self.assertNotIn("load_forex_signal_dashboard", function_source)
        self.assertNotIn("load_timeframe_optimization_results", function_source)
        self.assertNotIn("recalculate_research=True", function_source)

    def _tree(self) -> ast.AST:
        return parse_ast(self.DASHBOARD_PATH)

    def _imports(self) -> set[str]:
        return imports_from(self.DASHBOARD_PATH)

    def _call_names(self) -> set[str]:
        return calls_from(self.DASHBOARD_PATH)

    def _attribute_names(self) -> set[str]:
        return attributes_from(self.DASHBOARD_PATH)

    def _service_method_calls(self) -> list[str]:
        calls = {
            node.func.attr
            for node in ast.walk(self._tree())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "service"
        }
        return sorted(calls)

    def _dashboard_service_facade_calls(self) -> list[str]:
        calls = set(self._service_method_calls())
        for node in ast.walk(self._tree()):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == "get_dashboard_service"
            ):
                calls.add(node.func.attr)
        return sorted(calls)


if __name__ == "__main__":
    unittest.main()
