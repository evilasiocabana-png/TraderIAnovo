"""Testes do perfil oficial de pesquisa de Alpha."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.alpha_research_profile import AlphaResearchProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaResearchProfileTest(unittest.TestCase):
    """Valida contrato imutavel do perfil de pesquisa."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaResearchProfile))
        self.assertTrue(AlphaResearchProfile.__dataclass_params__.frozen)

    def test_profile_contem_campos_obrigatorios(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.alpha_id, "Alpha001")
        self.assertEqual(profile.alpha_name, "Alpha 001 IORB")
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.description, "Perfil oficial de pesquisa.")
        self.assertEqual(profile.market, "WDO")
        self.assertEqual(profile.timeframe, "1m")
        self.assertEqual(profile.status, "ACTIVE")
        self.assertEqual(profile.current_stage, "RESEARCH")
        self.assertEqual(profile.validation_level, "STATISTICAL")
        self.assertEqual(profile.configuration_version, 1)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.status = "CHANGED"

    def test_profile_nao_executa_pesquisa_ou_calculos(self) -> None:
        source = read_source(Path("research/portfolio/alpha_research_profile.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/alpha_research_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> AlphaResearchProfile:
        return AlphaResearchProfile(
            alpha_id="Alpha001",
            alpha_name="Alpha 001 IORB",
            version=1,
            description="Perfil oficial de pesquisa.",
            market="WDO",
            timeframe="1m",
            status="ACTIVE",
            current_stage="RESEARCH",
            validation_level="STATISTICAL",
            configuration_version=1,
        )


if __name__ == "__main__":
    unittest.main()
