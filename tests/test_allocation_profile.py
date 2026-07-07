"""Testes do contrato oficial de perfil de alocacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_profile import AllocationProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AllocationProfileTest(unittest.TestCase):
    """Valida contrato puro para perfis de alocacao."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationProfile))
        self.assertTrue(AllocationProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AllocationProfile)]

        self.assertEqual(
            field_names,
            [
                "profile_id",
                "name",
                "description",
                "capital",
                "allocation_method",
                "alpha_ids",
                "max_allocation_per_alpha",
                "max_total_exposure",
                "created_at",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = AllocationProfile.__annotations__

        self.assertEqual(annotations["profile_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["description"], "str")
        self.assertEqual(annotations["capital"], "float")
        self.assertEqual(annotations["allocation_method"], "str")
        self.assertEqual(annotations["alpha_ids"], "tuple[str, ...]")
        self.assertEqual(annotations["max_allocation_per_alpha"], "float")
        self.assertEqual(annotations["max_total_exposure"], "float")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_perfil_de_alocacao(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.profile_id, "allocation-balanced-001")
        self.assertEqual(profile.name, "Balanced Alpha Allocation")
        self.assertEqual(profile.description, "Perfil institucional de teste.")
        self.assertEqual(profile.capital, 100000.0)
        self.assertEqual(profile.allocation_method, "EQUAL_WEIGHT")
        self.assertEqual(profile.alpha_ids, ("Alpha001", "Alpha002"))
        self.assertEqual(profile.max_allocation_per_alpha, 0.5)
        self.assertEqual(profile.max_total_exposure, 0.8)
        self.assertEqual(profile.created_at, "2026-06-28T01:15:00-03:00")
        self.assertEqual(profile.metadata["source"], "unit-test")

    def test_profile_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "unit-test"}

        profile = AllocationProfile(
            profile_id="allocation-balanced-001",
            name="Balanced Alpha Allocation",
            description="Perfil institucional de teste.",
            capital=100000.0,
            allocation_method="EQUAL_WEIGHT",
            alpha_ids=("Alpha001", "Alpha002"),
            max_allocation_per_alpha=0.5,
            max_total_exposure=0.8,
            created_at="2026-06-28T01:15:00-03:00",
            metadata=metadata,
        )

        self.assertIs(profile.metadata, metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.capital = 1.0

    def test_profile_nao_calcula_pesos_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/portfolio/allocation_profile.py"))
        forbidden_fragments = (
            "def ",
            "sum(",
            "max(",
            "min(",
            "round(",
            "ResearchRunner",
            "ResearchPipeline",
            "PortfolioResearch",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".calculate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/allocation_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> AllocationProfile:
        return AllocationProfile(
            profile_id="allocation-balanced-001",
            name="Balanced Alpha Allocation",
            description="Perfil institucional de teste.",
            capital=100000.0,
            allocation_method="EQUAL_WEIGHT",
            alpha_ids=("Alpha001", "Alpha002"),
            max_allocation_per_alpha=0.5,
            max_total_exposure=0.8,
            created_at="2026-06-28T01:15:00-03:00",
            metadata={"source": "unit-test"},
        )


if __name__ == "__main__":
    unittest.main()
