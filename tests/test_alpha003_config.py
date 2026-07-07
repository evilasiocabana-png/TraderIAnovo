"""Testes da configuracao oficial da Alpha003."""

from dataclasses import FrozenInstanceError, MISSING, fields, is_dataclass
from pathlib import Path
import unittest

from core.configuration_manager import ConfigurationManager
from strategies.alpha003.alpha003_config import Alpha003Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha003ConfigTest(unittest.TestCase):
    """Valida contrato parametrizavel sem implementar estrategia."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_config_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha003Config))
        self.assertTrue(Alpha003Config.__dataclass_params__.frozen)

    def test_config_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(Alpha003Config)]

        self.assertEqual(
            field_names,
            [
                "session_start",
                "session_end",
                "stop_points",
                "target_points",
                "minimum_volume",
                "minimum_volatility",
                "minimum_confidence",
                "risk_profile",
            ],
        )

    def test_config_possui_type_hints_explicitos(self) -> None:
        annotations = Alpha003Config.__annotations__

        self.assertEqual(annotations["session_start"], "str")
        self.assertEqual(annotations["session_end"], "str")
        self.assertEqual(annotations["stop_points"], "float")
        self.assertEqual(annotations["target_points"], "float")
        self.assertEqual(annotations["minimum_volume"], "float")
        self.assertEqual(annotations["minimum_volatility"], "float")
        self.assertEqual(annotations["minimum_confidence"], "float")
        self.assertEqual(annotations["risk_profile"], "str")

    def test_todos_os_parametros_sao_configuraveis_sem_defaults(self) -> None:
        for field in fields(Alpha003Config):
            with self.subTest(field=field.name):
                self.assertIs(field.default, MISSING)
                self.assertIs(field.default_factory, MISSING)

    def test_config_pode_ser_criada_com_parametros_explicitos(self) -> None:
        config = self._config()

        self.assertEqual(config.session_start, "09:00")
        self.assertEqual(config.session_end, "18:00")
        self.assertEqual(config.stop_points, 50.0)
        self.assertEqual(config.target_points, 100.0)
        self.assertEqual(config.minimum_volume, 1000.0)
        self.assertEqual(config.minimum_volatility, 20.0)
        self.assertEqual(config.minimum_confidence, 0.7)
        self.assertEqual(config.risk_profile, "research-only")

    def test_config_reutiliza_configuration_manager(self) -> None:
        ConfigurationManager.update_configuration(
            stop_points=40.0,
            target_points=90.0,
            minimum_confidence=0.75,
        )

        config = Alpha003Config.from_configuration_manager(
            session_start="09:00",
            session_end="17:30",
            minimum_volume=1500.0,
            minimum_volatility=25.0,
            risk_profile="conservative-research",
        )

        self.assertEqual(config.session_start, "09:00")
        self.assertEqual(config.session_end, "17:30")
        self.assertEqual(config.stop_points, 40.0)
        self.assertEqual(config.target_points, 90.0)
        self.assertEqual(config.minimum_confidence, 0.75)
        self.assertEqual(config.minimum_volume, 1500.0)
        self.assertEqual(config.minimum_volatility, 25.0)
        self.assertEqual(config.risk_profile, "conservative-research")

    def test_config_e_imutavel(self) -> None:
        config = self._config()

        with self.assertRaises(FrozenInstanceError):
            config.stop_points = 10.0

    def test_config_nao_altera_alpha001_alpha002_domain_ou_risk(self) -> None:
        source = read_source(Path("strategies/alpha003/alpha003_config.py"))
        forbidden_fragments = (
            "Alpha001Config",
            "Alpha002Config",
            "class Alpha001",
            "class Alpha002",
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
        path = Path("strategies/alpha003/alpha003_config.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha.alpha001_config",
            "strategies.alpha002.alpha002_config",
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

    def _config(self) -> Alpha003Config:
        return Alpha003Config(
            session_start="09:00",
            session_end="18:00",
            stop_points=50.0,
            target_points=100.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="research-only",
        )


if __name__ == "__main__":
    unittest.main()
