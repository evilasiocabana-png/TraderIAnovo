"""Testes do perfil oficial de validacao Walk-Forward."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.walk_forward_profile import WalkForwardProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class WalkForwardProfileTest(unittest.TestCase):
    """Valida contrato puro para campanhas Walk-Forward."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardProfile))
        self.assertTrue(WalkForwardProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(WalkForwardProfile)],
            [
                "profile_id",
                "training_window",
                "validation_window",
                "testing_window",
                "rolling_window",
                "minimum_samples",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = WalkForwardProfile.__annotations__

        self.assertEqual(annotations["profile_id"], "str")
        self.assertEqual(annotations["training_window"], "int")
        self.assertEqual(annotations["validation_window"], "int")
        self.assertEqual(annotations["testing_window"], "int")
        self.assertEqual(annotations["rolling_window"], "int")
        self.assertEqual(annotations["minimum_samples"], "int")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_configuracao_walk_forward(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.profile_id, "walk-forward-balanced-001")
        self.assertEqual(profile.training_window, 120)
        self.assertEqual(profile.validation_window, 30)
        self.assertEqual(profile.testing_window, 30)
        self.assertEqual(profile.rolling_window, 15)
        self.assertEqual(profile.minimum_samples, 500)
        self.assertEqual(profile.metadata["campaign"], "alpha-research")

    def test_profile_preserva_metadata_recebido(self) -> None:
        metadata = {"campaign": "alpha-research"}

        profile = WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=120,
            validation_window=30,
            testing_window=30,
            rolling_window=15,
            minimum_samples=500,
            metadata=metadata,
        )

        self.assertIs(profile.metadata, metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.training_window = 1

    def test_profile_nao_executa_validacao_replay_ou_pipeline(self) -> None:
        source = read_source(Path("research/validation/walk_forward_profile.py"))
        forbidden_fragments = (
            "def ",
            "ReplayEngine",
            "ResearchPipeline",
            "Alpha001WalkForwardEngine",
            "calculate",
            "validate",
            "run",
            "next_candle",
            "open(",
            "write",
            "Dashboard",
            "streamlit",
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

    def test_profile_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/validation/walk_forward_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> WalkForwardProfile:
        return WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=120,
            validation_window=30,
            testing_window=30,
            rolling_window=15,
            minimum_samples=500,
            metadata={"campaign": "alpha-research"},
        )


if __name__ == "__main__":
    unittest.main()
