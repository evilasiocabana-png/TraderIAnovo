"""Testes do perfil oficial de estrategia."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from strategies.strategy_profile import StrategyProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StrategyProfileTest(unittest.TestCase):
    """Valida DTO imutavel de perfil de estrategia."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StrategyProfile))
        self.assertTrue(StrategyProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StrategyProfile)],
            [
                "strategy_id",
                "name",
                "family",
                "asset_class",
                "supported_markets",
                "supported_timeframes",
                "holding_period",
                "research_status",
                "version",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = StrategyProfile.__annotations__

        self.assertEqual(annotations["strategy_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["family"], "str")
        self.assertEqual(annotations["asset_class"], "str")
        self.assertEqual(annotations["supported_markets"], "tuple[str, ...]")
        self.assertEqual(annotations["supported_timeframes"], "tuple[str, ...]")
        self.assertEqual(annotations["holding_period"], "str")
        self.assertEqual(annotations["research_status"], "str")
        self.assertEqual(annotations["version"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_estrategia(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.strategy_id, "Alpha003")
        self.assertEqual(profile.name, "Alpha003")
        self.assertEqual(profile.family, "INTRADAY")
        self.assertEqual(profile.asset_class, "FUTURES")
        self.assertEqual(profile.supported_markets, ("WDO",))
        self.assertEqual(profile.supported_timeframes, ("1m", "5m"))
        self.assertEqual(profile.holding_period, "INTRADAY")
        self.assertEqual(profile.research_status, "VALIDATION")
        self.assertEqual(profile.version, "1.0")
        self.assertEqual(profile.metadata["source"], "unit-test")

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.research_status = "APPROVED"

    def test_profile_nao_executa_logica(self) -> None:
        public_methods = [
            name for name in dir(StrategyProfile)
            if not name.startswith("_") and callable(getattr(StrategyProfile, name))
        ]

        self.assertEqual(public_methods, [])

    def test_profile_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("strategies/strategy_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "domain.contracts.strategy_signal",
            "StrategySignal",
            "replay",
            "research",
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
        source = read_source(Path("strategies/strategy_profile.py"))
        forbidden_fragments = (
            "StrategySignal",
            "ReplayEngine",
            "ResearchPipeline",
            "ResearchRunner",
            "Dashboard",
            "streamlit",
            "DecisionPipeline",
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

    def _profile(self) -> StrategyProfile:
        return StrategyProfile(
            strategy_id="Alpha003",
            name="Alpha003",
            family="INTRADAY",
            asset_class="FUTURES",
            supported_markets=("WDO",),
            supported_timeframes=("1m", "5m"),
            holding_period="INTRADAY",
            research_status="VALIDATION",
            version="1.0",
            metadata={"source": "unit-test"},
        )


if __name__ == "__main__":
    unittest.main()
