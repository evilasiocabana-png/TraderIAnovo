"""Contratos arquiteturais da configuracao do TraderIA_WDO."""

from __future__ import annotations

import ast
import importlib
from dataclasses import fields, is_dataclass
from pathlib import Path
import unittest

from application.configuration_service import ConfigurationData, ConfigurationService
from application.dashboard_service import DashboardData, DashboardService
from core.configuration_manager import ConfigurationManager, SystemConfiguration
from tests.architecture_test_utils import calls_from, imports_from, parse_ast, read_source


class ConfigurationContractsTest(unittest.TestCase):
    """Protege ConfigurationManager, ConfigurationService e fachada do Dashboard."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    CENTRAL_CONFIGURATION_FIELDS = {
        "symbol",
        "initial_capital",
        "contracts",
        "stop_points",
        "target_points",
        "max_daily_loss",
        "max_daily_gain",
        "max_daily_operations",
        "minimum_score",
        "minimum_confidence",
        "simulation_mode",
        "version",
        "quantitative_score_candles_loaded",
        "quantitative_score_feature_lookback",
        "quantitative_score_forward_return_candles",
        "quantitative_score_fast_ma_period",
        "quantitative_score_slow_ma_period",
        "quantitative_score_rsi_period",
        "quantitative_score_atr_period",
        "quantitative_score_volatility_period",
        "quantitative_score_min_sample_size",
        "quantitative_score_min_profit_factor",
        "quantitative_score_min_win_rate",
        "quantitative_score_max_allowed_drawdown",
        "quantitative_score_confidence_floor",
        "quantitative_score_confidence_ceiling",
        "quantitative_score_volatility_bucket_method",
        "quantitative_score_volatility_low_threshold",
        "quantitative_score_volatility_high_threshold",
        "quantitative_score_ma_flat_threshold",
        "quantitative_score_ma_strong_threshold",
        "quantitative_score_rsi_oversold_threshold",
        "quantitative_score_rsi_overbought_threshold",
        "timeframe_optimizer_timeframes",
        "timeframe_optimizer_min_sample_size",
        "timeframe_optimizer_min_profit_factor",
        "timeframe_optimizer_min_win_rate",
        "timeframe_optimizer_max_allowed_drawdown",
        "timeframe_optimizer_min_confidence",
        "mt5_fast_refresh_enabled",
        "research_recalculate_on_every_refresh",
        "timeframe_optimizer_auto_run",
        "mt5_diagnostics_compact_mode",
        "forex_session_filter_enabled",
    }
    DASHBOARD_CONFIGURATION_FIELDS = {
        "symbol",
        "initial_capital",
        "contracts",
        "stop_points",
        "target_points",
        "max_daily_loss",
        "max_daily_gain",
        "minimum_score",
        "minimum_confidence",
        "simulation_mode",
        "version",
        "quantitative_score_candles_loaded",
        "quantitative_score_feature_lookback",
        "quantitative_score_forward_return_candles",
        "quantitative_score_fast_ma_period",
        "quantitative_score_slow_ma_period",
        "quantitative_score_rsi_period",
        "quantitative_score_atr_period",
        "quantitative_score_volatility_period",
        "quantitative_score_min_sample_size",
        "quantitative_score_min_profit_factor",
        "quantitative_score_min_win_rate",
        "quantitative_score_max_allowed_drawdown",
        "quantitative_score_confidence_floor",
        "quantitative_score_confidence_ceiling",
        "quantitative_score_volatility_bucket_method",
        "quantitative_score_volatility_low_threshold",
        "quantitative_score_volatility_high_threshold",
        "quantitative_score_ma_flat_threshold",
        "quantitative_score_ma_strong_threshold",
        "quantitative_score_rsi_oversold_threshold",
        "quantitative_score_rsi_overbought_threshold",
        "timeframe_optimizer_timeframes",
        "timeframe_optimizer_min_sample_size",
        "timeframe_optimizer_min_profit_factor",
        "timeframe_optimizer_min_win_rate",
        "timeframe_optimizer_max_allowed_drawdown",
        "timeframe_optimizer_min_confidence",
        "mt5_fast_refresh_enabled",
        "research_recalculate_on_every_refresh",
        "timeframe_optimizer_auto_run",
        "mt5_diagnostics_compact_mode",
        "forex_session_filter_enabled",
    }
    CONFIGURATION_SERVICE_METHODS = {
        "get_configuration_data",
        "update_configuration",
        "list_presets",
        "save_preset",
        "load_preset",
        "delete_preset",
    }
    DASHBOARD_DISPLAYED_CONFIGURATION_FIELDS = {
        "quantitative_score_candles_loaded",
        "quantitative_score_feature_lookback",
        "quantitative_score_forward_return_candles",
        "quantitative_score_fast_ma_period",
        "quantitative_score_slow_ma_period",
        "quantitative_score_rsi_period",
        "quantitative_score_atr_period",
        "quantitative_score_volatility_bucket_method",
        "quantitative_score_min_sample_size",
        "quantitative_score_min_profit_factor",
        "quantitative_score_min_win_rate",
        "quantitative_score_max_allowed_drawdown",
        "quantitative_score_confidence_floor",
        "quantitative_score_confidence_ceiling",
        "quantitative_score_volatility_low_threshold",
        "quantitative_score_volatility_high_threshold",
        "quantitative_score_ma_flat_threshold",
        "quantitative_score_ma_strong_threshold",
        "forex_session_filter_enabled",
    }

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_componentes_de_configuracao_importam_sem_excecao(self) -> None:
        components = {
            "core.configuration_manager": ("ConfigurationManager", "SystemConfiguration"),
            "application.configuration_service": (
                "ConfigurationService",
                "ConfigurationData",
            ),
            "application.dashboard_service": ("DashboardService",),
        }

        for module_name, names in components.items():
            module = importlib.import_module(module_name)
            for name in names:
                with self.subTest(component=f"{module_name}.{name}"):
                    self.assertTrue(hasattr(module, name))

    def test_componentes_de_configuracao_instanciam_sem_excecao(self) -> None:
        self.assertIsInstance(ConfigurationManager.get_configuration(), SystemConfiguration)
        self.assertIsInstance(ConfigurationService(), ConfigurationService)
        self.assertIsInstance(DashboardService(), DashboardService)

    def test_system_configuration_mantem_campos_essenciais(self) -> None:
        self.assertTrue(is_dataclass(SystemConfiguration))
        field_names = {field.name for field in fields(SystemConfiguration)}

        self.assertEqual(
            self.CENTRAL_CONFIGURATION_FIELDS - field_names,
            set(),
            "SystemConfiguration perdeu campos essenciais.",
        )

    def test_configuration_data_mantem_campos_expostos_ao_dashboard(self) -> None:
        self.assertTrue(is_dataclass(ConfigurationData))
        field_names = {field.name for field in fields(ConfigurationData)}

        self.assertEqual(
            self.DASHBOARD_CONFIGURATION_FIELDS - field_names,
            set(),
            "ConfigurationData perdeu campos expostos ao Dashboard.",
        )

    def test_configuration_manager_expoe_contrato_publico_central(self) -> None:
        required = {
            "get_configuration",
            "update_configuration",
            "reset_configuration",
            "save_preset",
            "load_preset",
            "list_presets",
            "delete_preset",
        }

        for method in required:
            with self.subTest(method=method):
                self.assertTrue(callable(getattr(ConfigurationManager, method, None)))

    def test_configuration_service_expoe_metodos_publicos_esperados(self) -> None:
        public_methods = self._public_methods(
            Path("application/configuration_service.py"),
            "ConfigurationService",
        )

        self.assertEqual(
            self.CONFIGURATION_SERVICE_METHODS - public_methods,
            set(),
        )

    def test_configuration_service_obtem_atualiza_e_gerencia_presets(self) -> None:
        service = ConfigurationService()

        initial = service.get_configuration_data()
        updated = service.update_configuration(symbol="WIN", contracts=2)
        service.save_preset("agressivo")
        service.update_configuration(symbol="WDO", contracts=1)
        loaded = service.load_preset("agressivo")
        presets = service.list_presets()
        service.delete_preset("agressivo")

        self.assertIsInstance(initial, ConfigurationData)
        self.assertEqual(updated.symbol, "WIN")
        self.assertEqual(updated.contracts, 2)
        self.assertEqual(loaded.symbol, "WIN")
        self.assertEqual(presets, ["agressivo"])
        self.assertEqual(service.list_presets(), [])

    def test_persiste_preferencia_de_filtro_de_sessao_forex(self) -> None:
        service = ConfigurationService()

        initial = service.get_configuration_data()
        enabled = service.update_configuration(forex_session_filter_enabled=True)
        updated = service.update_configuration(forex_session_filter_enabled=False)

        self.assertFalse(initial.forex_session_filter_enabled)
        self.assertTrue(enabled.forex_session_filter_enabled)
        self.assertFalse(updated.forex_session_filter_enabled)
        self.assertFalse(service.get_configuration_data().forex_session_filter_enabled)

    def test_configuration_service_repassa_validacoes_do_manager(self) -> None:
        with self.assertRaisesRegex(ValueError, "stop_points"):
            ConfigurationService().update_configuration(stop_points=-1)

        with self.assertRaisesRegex(ValueError, "Campos invalidos"):
            ConfigurationService().update_configuration(campo_invalido=1)

    def test_dashboard_service_expoe_configuracao_via_fachada(self) -> None:
        service = DashboardService()

        configuration = service.update_configuration(symbol="WIN", contracts=3)
        data = service.get_dashboard_data()

        self.assertIsInstance(configuration, ConfigurationData)
        self.assertIsInstance(data, DashboardData)
        self.assertIsInstance(data.configuration_data, ConfigurationData)
        self.assertEqual(data.configuration_data.symbol, "WIN")
        self.assertEqual(data.configuration_data.contracts, 3)

    def test_dashboard_service_expoe_presets_sem_dashboard_acessar_manager(
        self,
    ) -> None:
        service = DashboardService()
        service.update_configuration(symbol="WIN")
        service.save_configuration_preset("preset")
        service.update_configuration(symbol="WDO")

        loaded = service.load_configuration_preset("preset")

        self.assertEqual(service.list_configuration_presets(), ["preset"])
        self.assertEqual(loaded.symbol, "WIN")
        service.delete_configuration_preset("preset")
        self.assertEqual(service.list_configuration_presets(), [])

    def test_dashboard_app_nao_importa_configuracao_diretamente(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))
        forbidden = {
            "core.configuration_manager",
            "ConfigurationManager",
            "SystemConfiguration",
            "application.configuration_service",
            "ConfigurationService",
            "config",
            "database",
            "sqlite3",
            "market_data",
            "providers",
            "adapters",
        }

        self.assertTrue(
            forbidden.isdisjoint(imports),
            f"dashboard_app.py acessa configuracao diretamente: "
            f"{sorted(forbidden & imports)}",
        )
        self.assertIn("application.dashboard_service", imports)

    def test_dashboard_app_renderiza_campos_de_configuracao_via_dto(self) -> None:
        source = read_source(Path("dashboard_app.py"))

        for field_name in self.DASHBOARD_DISPLAYED_CONFIGURATION_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, source)
        self.assertIn("update_configuration", source)
        self.assertIn("save_configuration_preset", source)
        self.assertIn("load_configuration_preset", source)
        self.assertIn("delete_configuration_preset", source)

    def test_componentes_de_configuracao_nao_importam_ui_broker_ou_data_source(
        self,
    ) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "broker",
            "core.broker",
            "corretora",
            "mt5",
            "MetaTrader5",
            "pandas",
            "duckdb",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }

        for path in (
            Path("core/configuration_manager.py"),
            Path("application/configuration_service.py"),
            Path("application/dashboard_service.py"),
        ):
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertTrue(
                    forbidden.isdisjoint(imports),
                    f"{path} importou acoplamento proibido: "
                    f"{sorted(forbidden & imports)}",
                )

    def test_componentes_de_configuracao_nao_acessam_arquivos_fisicos(self) -> None:
        forbidden_calls = {
            "open",
            "read_csv",
            "read_parquet",
            "connect",
            "glob",
            "iterdir",
            "listdir",
        }

        for path in (
            Path("core/configuration_manager.py"),
            Path("application/configuration_service.py"),
            Path("application/dashboard_service.py"),
        ):
            with self.subTest(path=str(path)):
                calls = self._calls(path)
                self.assertTrue(
                    forbidden_calls.isdisjoint(calls),
                    f"{path} acessa arquivo/persistencia diretamente: "
                    f"{sorted(forbidden_calls & calls)}",
                )

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _calls(self, path: Path) -> set[str]:
        return calls_from(path)

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


if __name__ == "__main__":
    unittest.main()
