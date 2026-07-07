"""Testes da configuracao oficial da Alpha002."""

from dataclasses import FrozenInstanceError, MISSING, fields, is_dataclass
from pathlib import Path
import unittest

from core.configuration_manager import ConfigurationManager
from strategies.alpha002.alpha002_config import Alpha002Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha002ConfigTest(unittest.TestCase):
    """Valida contrato parametrizavel sem implementar estrategia."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_config_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha002Config))
        self.assertTrue(Alpha002Config.__dataclass_params__.frozen)

    def test_config_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(Alpha002Config)]

        self.assertEqual(
            field_names,
            [
                "opening_range",
                "stop_points",
                "target_points",
                "minimum_volume",
                "minimum_volatility",
                "minimum_confidence",
                "session_start",
                "session_end",
            ],
        )

    def test_config_possui_type_hints_explicitos(self) -> None:
        annotations = Alpha002Config.__annotations__

        self.assertEqual(annotations["opening_range"], "int")
        self.assertEqual(annotations["stop_points"], "float")
        self.assertEqual(annotations["target_points"], "float")
        self.assertEqual(annotations["minimum_volume"], "float")
        self.assertEqual(annotations["minimum_volatility"], "float")
        self.assertEqual(annotations["minimum_confidence"], "float")
        self.assertEqual(annotations["session_start"], "str")
        self.assertEqual(annotations["session_end"], "str")

    def test_todos_os_parametros_sao_configuraveis_sem_defaults(self) -> None:
        for field in fields(Alpha002Config):
            with self.subTest(field=field.name):
                self.assertIs(field.default, MISSING)
                self.assertIs(field.default_factory, MISSING)

    def test_config_pode_ser_criada_com_parametros_explicitos(self) -> None:
        config = self._config()

        self.assertEqual(config.opening_range, 15)
        self.assertEqual(config.stop_points, 50.0)
        self.assertEqual(config.target_points, 100.0)
        self.assertEqual(config.minimum_volume, 1000.0)
        self.assertEqual(config.minimum_volatility, 20.0)
        self.assertEqual(config.minimum_confidence, 0.7)
        self.assertEqual(config.session_start, "09:00")
        self.assertEqual(config.session_end, "18:00")

    def test_config_reutiliza_configuration_manager(self) -> None:
        ConfigurationManager.update_configuration(
            stop_points=35.0,
            target_points=80.0,
            minimum_confidence=0.65,
        )

        config = Alpha002Config.from_configuration_manager(
            opening_range=20,
            minimum_volume=1500.0,
            minimum_volatility=25.0,
            session_start="09:00",
            session_end="17:30",
        )

        self.assertEqual(config.opening_range, 20)
        self.assertEqual(config.stop_points, 35.0)
        self.assertEqual(config.target_points, 80.0)
        self.assertEqual(config.minimum_confidence, 0.65)
        self.assertEqual(config.minimum_volume, 1500.0)
        self.assertEqual(config.minimum_volatility, 25.0)
        self.assertEqual(config.session_start, "09:00")
        self.assertEqual(config.session_end, "17:30")

    def test_config_e_imutavel(self) -> None:
        config = self._config()

        with self.assertRaises(FrozenInstanceError):
            config.stop_points = 10.0

    def test_config_nao_altera_alpha001_domain_replay_ou_risk(self) -> None:
        source = read_source(Path("strategies/alpha002/alpha002_config.py"))
        forbidden_fragments = (
            "Alpha001Config",
            "class Alpha001",
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
        path = Path("strategies/alpha002/alpha002_config.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha.alpha001_config",
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

    def _config(self) -> Alpha002Config:
        return Alpha002Config(
            opening_range=15,
            stop_points=50.0,
            target_points=100.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            session_start="09:00",
            session_end="18:00",
        )


if __name__ == "__main__":
    unittest.main()
