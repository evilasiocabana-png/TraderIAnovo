"""Testes dos perfis oficiais de timeframe do Research Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.research_timeframe_profile import (
    DAILY_TIMEFRAME_PROFILE,
    INTRADAY_TIMEFRAME_PROFILE,
    MONTHLY_TIMEFRAME_PROFILE,
    SUPPORTED_RESEARCH_TIMEFRAME_PROFILES,
    WEEKLY_TIMEFRAME_PROFILE,
    ResearchTimeframeProfile,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchTimeframeProfileTest(unittest.TestCase):
    """Valida DTO imutavel de timeframe de pesquisa."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchTimeframeProfile))
        self.assertTrue(ResearchTimeframeProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ResearchTimeframeProfile)],
            [
                "timeframe",
                "minimum_history",
                "recommended_campaign_size",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = ResearchTimeframeProfile.__annotations__

        self.assertEqual(annotations["timeframe"], "str")
        self.assertEqual(annotations["minimum_history"], "str")
        self.assertEqual(annotations["recommended_campaign_size"], "int")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_timeframe_de_pesquisa(self) -> None:
        profile = ResearchTimeframeProfile(
            timeframe="INTRADAY",
            minimum_history="3 months",
            recommended_campaign_size=30,
            metadata={"source": "unit-test"},
        )

        self.assertEqual(profile.timeframe, "INTRADAY")
        self.assertEqual(profile.minimum_history, "3 months")
        self.assertEqual(profile.recommended_campaign_size, 30)
        self.assertEqual(profile.metadata["source"], "unit-test")

    def test_profile_e_imutavel(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            INTRADAY_TIMEFRAME_PROFILE.timeframe = "DAILY"

    def test_perfis_oficiais_sao_declarados(self) -> None:
        self.assertEqual(
            SUPPORTED_RESEARCH_TIMEFRAME_PROFILES,
            (
                INTRADAY_TIMEFRAME_PROFILE,
                DAILY_TIMEFRAME_PROFILE,
                WEEKLY_TIMEFRAME_PROFILE,
                MONTHLY_TIMEFRAME_PROFILE,
            ),
        )
        self.assertEqual(
            tuple(profile.timeframe for profile in SUPPORTED_RESEARCH_TIMEFRAME_PROFILES),
            ("INTRADAY", "DAILY", "WEEKLY", "MONTHLY"),
        )

    def test_profile_nao_executa_logica(self) -> None:
        public_methods = [
            name for name in dir(ResearchTimeframeProfile)
            if not name.startswith("_")
            and callable(getattr(ResearchTimeframeProfile, name))
        ]

        self.assertEqual(public_methods, [])

    def test_profile_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("research/research_timeframe_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "strategies",
            "alpha",
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
        source = read_source(Path("research/research_timeframe_profile.py"))
        forbidden_fragments = (
            "ReplayEngine",
            "ResearchPipeline",
            "ResearchRunner",
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


if __name__ == "__main__":
    unittest.main()
