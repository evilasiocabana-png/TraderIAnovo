"""Testes da configuracao oficial da Alpha301."""

from dataclasses import FrozenInstanceError, MISSING, fields, is_dataclass
from pathlib import Path
import unittest

from core.configuration_manager import ConfigurationManager
from strategies.alpha301.alpha301_config import Alpha301Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha301ConfigTest(unittest.TestCase):
    """Valida contrato parametrizavel sem implementar estrategia."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_config_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha301Config))
        self.assertTrue(Alpha301Config.__dataclass_params__.frozen)

    def test_config_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(Alpha301Config)]

        self.assertEqual(
            field_names,
            [
                "timeframe",
                "holding_period",
                "stop_points",
                "target_points",
                "minimum_volume",
                "minimum_volatility",
                "minimum_confidence",
                "risk_profile",
            ],
        )

    def test_config_possui_type_hints_explicitos(self) -> None:
        annotations = Alpha301Config.__annotations__

        self.assertEqual(annotations["timeframe"], "str")
        self.assertEqual(annotations["holding_period"], "str")
        self.assertEqual(annotations["stop_points"], "float")
        self.assertEqual(annotations["target_points"], "float")
        self.assertEqual(annotations["minimum_volume"], "float")
        self.assertEqual(annotations["minimum_volatility"], "float")
        self.assertEqual(annotations["minimum_confidence"], "float")
        self.assertEqual(annotations["risk_profile"], "str")

    def test_todos_os_parametros_sao_configuraveis_sem_defaults(self) -> None:
        for field in fields(Alpha301Config):
            with self.subTest(field=field.name):
                self.assertIs(field.default, MISSING)
                self.assertIs(field.default_factory, MISSING)

    def test_config_pode_ser_criada_com_parametros_explicitos(self) -> None:
        config = self._config()

        self.assertEqual(config.timeframe, "DAILY")
        self.assertEqual(config.holding_period, "LONG_SHORT")
        self.assertEqual(config.stop_points, 150.0)
        self.assertEqual(config.target_points, 300.0)
        self.assertEqual(config.minimum_volume, 4000.0)
        self.assertEqual(config.minimum_volatility, 25.0)
        self.assertEqual(config.minimum_confidence, 0.78)
        self.assertEqual(config.risk_profile, "long-short-research")

    def test_config_reutiliza_configuration_manager(self) -> None:
        ConfigurationManager.update_configuration(
            stop_points=160.0,
            target_points=320.0,
            minimum_confidence=0.82,
        )

        config = Alpha301Config.from_configuration_manager(
            timeframe="DAILY",
            holding_period="LONG_SHORT",
            minimum_volume=4500.0,
            minimum_volatility=28.0,
            risk_profile="conservative-long-short",
        )

        self.assertEqual(config.timeframe, "DAILY")
        self.assertEqual(config.holding_period, "LONG_SHORT")
        self.assertEqual(config.stop_points, 160.0)
        self.assertEqual(config.target_points, 320.0)
        self.assertEqual(config.minimum_confidence, 0.82)
        self.assertEqual(config.minimum_volume, 4500.0)
        self.assertEqual(config.minimum_volatility, 28.0)
        self.assertEqual(config.risk_profile, "conservative-long-short")

    def test_config_e_imutavel(self) -> None:
        config = self._config()

        with self.assertRaises(FrozenInstanceError):
            config.stop_points = 10.0

    def test_config_nao_altera_alphas_existentes_domain_ou_risk(self) -> None:
        source = read_source(Path("strategies/alpha301/alpha301_config.py"))
        forbidden_fragments = (
            "Alpha001Config",
            "Alpha002Config",
            "Alpha003Config",
            "Alpha101Config",
            "Alpha201Config",
            "class Alpha001",
            "class Alpha002",
            "class Alpha003",
            "class Alpha101",
            "class Alpha201",
            "StrategySignal",
            "ReplayEngine",
            "DecisionPipeline",
            "RiskEngine",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
            ".generate_signal(",
            ".next_candle(",
            ".processar(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_config_permanece_desacoplada_de_camadas_operacionais(self) -> None:
        path = Path("strategies/alpha301/alpha301_config.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha.alpha001_config",
            "strategies.alpha002.alpha002_config",
            "strategies.alpha003.alpha003_config",
            "strategies.alpha101.alpha101_config",
            "strategies.alpha201.alpha201_config",
            "domain",
            "replay",
            "application.replay_service",
            "risk.risk_engine",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
            "dashboard_app",
            "streamlit",
        }
        forbidden_calls = {
            "open",
            "avaliar",
            "processar",
            "execute",
            "run",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("core.configuration_manager", imports)

    def _config(self) -> Alpha301Config:
        return Alpha301Config(
            timeframe="DAILY",
            holding_period="LONG_SHORT",
            stop_points=150.0,
            target_points=300.0,
            minimum_volume=4000.0,
            minimum_volatility=25.0,
            minimum_confidence=0.78,
            risk_profile="long-short-research",
        )


if __name__ == "__main__":
    unittest.main()
