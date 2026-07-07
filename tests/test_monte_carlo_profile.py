"""Testes do perfil oficial de validacao Monte Carlo."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MonteCarloProfileTest(unittest.TestCase):
    """Valida contrato puro para validacao Monte Carlo."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloProfile))
        self.assertTrue(MonteCarloProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(MonteCarloProfile)],
            [
                "profile_id",
                "simulations",
                "random_seed",
                "confidence_level",
                "resampling_method",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = MonteCarloProfile.__annotations__

        self.assertEqual(annotations["profile_id"], "str")
        self.assertEqual(annotations["simulations"], "int")
        self.assertEqual(annotations["random_seed"], "int")
        self.assertEqual(annotations["confidence_level"], "float")
        self.assertEqual(annotations["resampling_method"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_configuracao_monte_carlo(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.profile_id, "monte-carlo-baseline-001")
        self.assertEqual(profile.simulations, 1000)
        self.assertEqual(profile.random_seed, 42)
        self.assertEqual(profile.confidence_level, 0.95)
        self.assertEqual(profile.resampling_method, "BOOTSTRAP_TRADES")
        self.assertEqual(profile.metadata["scope"], "validation")

    def test_profile_preserva_metadata_recebido(self) -> None:
        metadata = {"scope": "validation"}

        profile = MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=1000,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="BOOTSTRAP_TRADES",
            metadata=metadata,
        )

        self.assertIs(profile.metadata, metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.simulations = 1

    def test_profile_nao_executa_simulacoes_ou_acessa_replay(self) -> None:
        source = read_source(
            Path("research/validation/monte_carlo/monte_carlo_profile.py")
        )
        forbidden_fragments = (
            "def ",
            "random.",
            "shuffle",
            "sample",
            "simulate",
            "ValidationRunner",
            "ReplayEngine",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".calculate(",
            ".validate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/validation/monte_carlo/monte_carlo_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "random",
            "research.validation.experiment_validation_runner",
            "research.research_pipeline",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "validate",
            "simulate",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=1000,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="BOOTSTRAP_TRADES",
            metadata={"scope": "validation"},
        )


if __name__ == "__main__":
    unittest.main()
