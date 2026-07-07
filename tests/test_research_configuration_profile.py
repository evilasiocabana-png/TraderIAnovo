"""Testes do perfil oficial de configuracao de pesquisa."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.research_configuration_profile import ResearchConfigurationProfile
from research.research_timeframe_profile import INTRADAY_TIMEFRAME_PROFILE
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchConfigurationProfileTest(unittest.TestCase):
    """Valida DTO imutavel de configuracao de pesquisa."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchConfigurationProfile))
        self.assertTrue(ResearchConfigurationProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ResearchConfigurationProfile)],
            [
                "strategy_family",
                "timeframe_profile",
                "minimum_sample_size",
                "required_metrics",
                "validation_rules",
                "campaign_profile",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = ResearchConfigurationProfile.__annotations__

        self.assertEqual(annotations["strategy_family"], "str")
        self.assertEqual(
            annotations["timeframe_profile"],
            "ResearchTimeframeProfile",
        )
        self.assertEqual(annotations["minimum_sample_size"], "int")
        self.assertEqual(annotations["required_metrics"], "tuple[str, ...]")
        self.assertEqual(annotations["validation_rules"], "tuple[str, ...]")
        self.assertEqual(annotations["campaign_profile"], "Mapping[str, object]")

    def test_profile_representa_configuracao_de_pesquisa(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.strategy_family, "INTRADAY")
        self.assertIs(profile.timeframe_profile, INTRADAY_TIMEFRAME_PROFILE)
        self.assertEqual(profile.minimum_sample_size, 30)
        self.assertEqual(
            profile.required_metrics,
            ("profit_factor", "win_rate", "drawdown"),
        )
        self.assertEqual(
            profile.validation_rules,
            ("minimum_trades", "maximum_drawdown"),
        )
        self.assertEqual(profile.campaign_profile["campaign_size"], 30)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.minimum_sample_size = 10

    def test_profile_nao_executa_logica(self) -> None:
        public_methods = [
            name for name in dir(ResearchConfigurationProfile)
            if not name.startswith("_")
            and callable(getattr(ResearchConfigurationProfile, name))
        ]

        self.assertEqual(public_methods, [])

    def test_profile_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("research/research_configuration_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "strategies.alpha001_iorb_strategy",
            "strategies.alpha002",
            "strategies.alpha003",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "validate",
            "calculate",
            "run",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_profile_nao_contem_acoplamento_no_codigo_fonte(self) -> None:
        source = read_source(Path("research/research_configuration_profile.py"))
        forbidden_fragments = (
            "ReplayEngine",
            "ResearchRunner",
            "ResearchPipeline",
            "Alpha001",
            "Alpha002",
            "Alpha003",
            "StrategySignal",
            "Dashboard",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _profile(self) -> ResearchConfigurationProfile:
        return ResearchConfigurationProfile(
            strategy_family="INTRADAY",
            timeframe_profile=INTRADAY_TIMEFRAME_PROFILE,
            minimum_sample_size=30,
            required_metrics=("profit_factor", "win_rate", "drawdown"),
            validation_rules=("minimum_trades", "maximum_drawdown"),
            campaign_profile={"campaign_size": 30},
        )


if __name__ == "__main__":
    unittest.main()
