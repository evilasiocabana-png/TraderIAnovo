"""Testes do engine de pesos teoricos de alocacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_profile import AllocationProfile
from research.portfolio.allocation_weight_engine import (
    AllocationWeightEngine,
    AllocationWeightResult,
)
from research.portfolio.alpha_correlation_engine import AlphaCorrelationResult
from research.portfolio.alpha_registry import AlphaRegistry
from research.portfolio.alpha_research_profile import AlphaResearchProfile
from research.portfolio.portfolio_research_comparator import (
    PortfolioComparisonResult,
    PortfolioResearchComparison,
)
from research.portfolio.portfolio_research_report import PortfolioResearchReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AllocationWeightEngineTest(unittest.TestCase):
    """Valida pesos teoricos sem otimizacao matematica avancada."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationWeightResult))
        self.assertTrue(AllocationWeightResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AllocationWeightResult)]

        self.assertEqual(field_names, ["equal_weight", "risk_adjusted_weight"])

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = AllocationWeightResult.__annotations__

        self.assertEqual(annotations["equal_weight"], "Mapping[str, float]")
        self.assertEqual(annotations["risk_adjusted_weight"], "Mapping[str, float]")

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationWeightEngine))
        self.assertTrue(AllocationWeightEngine.__dataclass_params__.frozen)

    def test_engine_calcula_equal_weight(self) -> None:
        result = AllocationWeightEngine().calculate(self._profile(), self._report())

        self.assertEqual(
            result.equal_weight,
            {
                "Alpha001": 0.4,
                "Alpha002": 0.4,
            },
        )

    def test_engine_calcula_risk_adjusted_weight(self) -> None:
        result = AllocationWeightEngine().calculate(self._profile(), self._report())

        self.assertAlmostEqual(result.risk_adjusted_weight["Alpha001"], 0.4)
        self.assertAlmostEqual(result.risk_adjusted_weight["Alpha002"], 0.16)

    def test_engine_respeita_limite_por_alpha(self) -> None:
        profile = AllocationProfile(
            profile_id="allocation-capped",
            name="Capped",
            description="Perfil com limite menor.",
            capital=100000.0,
            allocation_method="RISK_ADJUSTED",
            alpha_ids=("Alpha001", "Alpha002"),
            max_allocation_per_alpha=0.25,
            max_total_exposure=0.8,
            created_at="2026-06-28T01:20:00-03:00",
            metadata={},
        )

        result = AllocationWeightEngine().calculate(profile, self._report())

        self.assertEqual(result.equal_weight["Alpha001"], 0.25)
        self.assertLessEqual(result.risk_adjusted_weight["Alpha001"], 0.25)

    def test_engine_usa_fallback_equal_weight_quando_scores_sao_zero(self) -> None:
        report = self._report(
            (
                self._comparison("Alpha001", profit_factor=0.0, max_drawdown=5.0),
                self._comparison("Alpha002", profit_factor=-1.0, max_drawdown=5.0),
            )
        )

        result = AllocationWeightEngine().calculate(self._profile(), report)

        self.assertEqual(result.risk_adjusted_weight, result.equal_weight)

    def test_engine_restringe_alphas_ao_profile(self) -> None:
        report = self._report(
            (
                self._comparison("Alpha001", profit_factor=2.0, max_drawdown=1.0),
                self._comparison("Alpha999", profit_factor=99.0, max_drawdown=1.0),
            )
        )

        result = AllocationWeightEngine().calculate(self._profile(), report)

        self.assertEqual(tuple(result.equal_weight.keys()), ("Alpha001",))
        self.assertNotIn("Alpha999", result.risk_adjusted_weight)

    def test_result_e_imutavel(self) -> None:
        result = AllocationWeightEngine().calculate(self._profile(), self._report())

        with self.assertRaises(FrozenInstanceError):
            result.equal_weight = {}

    def test_engine_nao_altera_profile_ou_report(self) -> None:
        profile = self._profile()
        report = self._report()

        AllocationWeightEngine().calculate(profile, report)

        self.assertEqual(profile.max_total_exposure, 0.8)
        self.assertEqual(report.comparison_result.total_results, 2)

    def test_engine_nao_implementa_otimizacoes_proibidas_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/portfolio/allocation_weight_engine.py"))
        forbidden_fragments = (
            "Markowitz",
            "HRP",
            "Black-Litterman",
            "Risk Parity",
            "optimiz",
            "scipy",
            "numpy",
            "ResearchRunner",
            "ResearchPipeline",
            "PortfolioResearchComparator",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".compare(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/allocation_weight_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.portfolio.portfolio_research_comparator",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "numpy",
            "scipy",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "compare",
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
            allocation_method="RISK_ADJUSTED",
            alpha_ids=("Alpha001", "Alpha002"),
            max_allocation_per_alpha=0.4,
            max_total_exposure=0.8,
            created_at="2026-06-28T01:20:00-03:00",
            metadata={"source": "unit-test"},
        )

    def _report(
        self,
        comparisons: tuple[PortfolioResearchComparison, ...] | None = None,
    ) -> PortfolioResearchReport:
        comparison_result = PortfolioComparisonResult(
            total_results=2,
            comparisons=comparisons
            or (
                self._comparison("Alpha001", profit_factor=3.0, max_drawdown=2.0),
                self._comparison("Alpha002", profit_factor=1.0, max_drawdown=3.0),
            ),
        )
        return PortfolioResearchReport(
            alpha_registry=AlphaRegistry(),
            alpha_profiles=(
                self._profile_for("Alpha001"),
                self._profile_for("Alpha002"),
            ),
            comparison_result=comparison_result,
            correlation_result=AlphaCorrelationResult(
                alpha_ids=("Alpha001", "Alpha002"),
                correlation_matrix=((1.0, 0.2), (0.2, 1.0)),
                average_correlation=0.2,
                highest_correlation=0.2,
                lowest_correlation=0.2,
            ),
        )

    def _comparison(
        self,
        alpha_id: str,
        profit_factor: float,
        max_drawdown: float,
    ) -> PortfolioResearchComparison:
        return PortfolioResearchComparison(
            alpha_id=alpha_id,
            total_trades=10,
            net_profit=100.0,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            expectancy=4.0,
            win_rate=0.6,
        )

    def _profile_for(self, alpha_id: str) -> AlphaResearchProfile:
        return AlphaResearchProfile(
            alpha_id=alpha_id,
            alpha_name=alpha_id,
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
