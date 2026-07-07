"""Testes do contrato oficial de otimizacao de portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_profile import AllocationProfile
from research.portfolio.portfolio_optimization_profile import (
    OptimizationGoal,
    PortfolioOptimizationProfile,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioOptimizationProfileTest(unittest.TestCase):
    """Valida contrato puro de perfil de otimizacao."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioOptimizationProfile))
        self.assertTrue(PortfolioOptimizationProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioOptimizationProfile)],
            [
                "profile_id",
                "capital",
                "allocation_method",
                "optimization_goal",
                "alpha_ids",
                "constraints",
                "created_at",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = PortfolioOptimizationProfile.__annotations__

        self.assertEqual(annotations["profile_id"], "str")
        self.assertEqual(annotations["capital"], "float")
        self.assertEqual(annotations["allocation_method"], "str")
        self.assertEqual(annotations["optimization_goal"], "OptimizationGoal")
        self.assertEqual(annotations["alpha_ids"], "tuple[str, ...]")
        self.assertEqual(annotations["constraints"], "Mapping[str, object]")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_optimization_goal_restringe_objetivos_permitidos(self) -> None:
        self.assertEqual(
            OptimizationGoal.__args__,
            ("MAX_RETURN", "MIN_RISK", "BALANCED"),
        )

    def test_profile_representa_configuracao_de_otimizacao(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.profile_id, "allocation-balanced-001")
        self.assertEqual(profile.capital, 100000.0)
        self.assertEqual(profile.allocation_method, "EQUAL_WEIGHT")
        self.assertEqual(profile.optimization_goal, "BALANCED")
        self.assertEqual(profile.alpha_ids, ("Alpha001", "Alpha301"))
        self.assertEqual(profile.constraints["max_total_exposure"], 0.8)
        self.assertEqual(profile.created_at, "2026-06-28T05:30:00-03:00")
        self.assertEqual(profile.metadata["source"], "unit-test")

    def test_from_allocation_profile_reutiliza_allocation_profile(self) -> None:
        allocation = self._allocation_profile()
        constraints = {
            "max_allocation_per_alpha": allocation.max_allocation_per_alpha,
            "max_total_exposure": allocation.max_total_exposure,
        }

        profile = PortfolioOptimizationProfile.from_allocation_profile(
            allocation_profile=allocation,
            optimization_goal="MIN_RISK",
            constraints=constraints,
        )

        self.assertEqual(profile.profile_id, allocation.profile_id)
        self.assertEqual(profile.capital, allocation.capital)
        self.assertEqual(profile.allocation_method, allocation.allocation_method)
        self.assertEqual(profile.optimization_goal, "MIN_RISK")
        self.assertEqual(profile.alpha_ids, allocation.alpha_ids)
        self.assertIs(profile.constraints, constraints)
        self.assertEqual(profile.created_at, allocation.created_at)
        self.assertIs(profile.metadata, allocation.metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.capital = 1.0

    def test_profile_nao_calcula_otimizacao_ou_acessa_pipeline(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_optimization_profile.py")
        )
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "Domain",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".calculate(",
            ".optimize(",
            "sum(",
            "max(",
            "min(",
            "sorted(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_optimization_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
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
            "optimize",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> PortfolioOptimizationProfile:
        return PortfolioOptimizationProfile(
            profile_id="allocation-balanced-001",
            capital=100000.0,
            allocation_method="EQUAL_WEIGHT",
            optimization_goal="BALANCED",
            alpha_ids=("Alpha001", "Alpha301"),
            constraints={"max_total_exposure": 0.8},
            created_at="2026-06-28T05:30:00-03:00",
            metadata={"source": "unit-test"},
        )

    def _allocation_profile(self) -> AllocationProfile:
        return AllocationProfile(
            profile_id="allocation-balanced-001",
            name="Balanced Alpha Allocation",
            description="Perfil institucional de teste.",
            capital=100000.0,
            allocation_method="EQUAL_WEIGHT",
            alpha_ids=("Alpha001", "Alpha301"),
            max_allocation_per_alpha=0.5,
            max_total_exposure=0.8,
            created_at="2026-06-28T05:30:00-03:00",
            metadata={"source": "allocation-profile"},
        )


if __name__ == "__main__":
    unittest.main()
