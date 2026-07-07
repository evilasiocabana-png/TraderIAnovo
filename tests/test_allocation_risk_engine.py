"""Testes do engine de risco teorico de alocacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_risk_engine import (
    AllocationRiskEngine,
    AllocationRiskResult,
)
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.alpha_correlation_engine import AlphaCorrelationResult
from research.portfolio.alpha_registry import AlphaRegistry
from research.portfolio.alpha_research_profile import AlphaResearchProfile
from research.portfolio.portfolio_research_comparator import (
    PortfolioComparisonResult,
    PortfolioResearchComparison,
)
from research.portfolio.portfolio_research_report import PortfolioResearchReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AllocationRiskEngineTest(unittest.TestCase):
    """Valida risco agregado sem alterar pesos ou metricas individuais."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationRiskResult))
        self.assertTrue(AllocationRiskResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AllocationRiskResult)]

        self.assertEqual(
            field_names,
            [
                "portfolio_exposure",
                "concentration_score",
                "aggregate_drawdown",
                "aggregate_risk_score",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = AllocationRiskResult.__annotations__

        self.assertEqual(annotations["portfolio_exposure"], "float")
        self.assertEqual(annotations["concentration_score"], "float")
        self.assertEqual(annotations["aggregate_drawdown"], "float")
        self.assertEqual(annotations["aggregate_risk_score"], "float")

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationRiskEngine))
        self.assertTrue(AllocationRiskEngine.__dataclass_params__.frozen)

    def test_engine_calcula_risco_da_alocacao(self) -> None:
        result = AllocationRiskEngine().calculate(self._weights(), self._report())

        self.assertAlmostEqual(result.portfolio_exposure, 0.6)
        self.assertEqual(result.concentration_score, 0.4)
        self.assertAlmostEqual(result.aggregate_drawdown, 1.8)
        self.assertAlmostEqual(result.aggregate_risk_score, 2.8)

    def test_engine_retorna_zero_para_pesos_vazios(self) -> None:
        result = AllocationRiskEngine().calculate(
            AllocationWeightResult(equal_weight={}, risk_adjusted_weight={}),
            self._report(),
        )

        self.assertEqual(result.portfolio_exposure, 0.0)
        self.assertEqual(result.concentration_score, 0.0)
        self.assertEqual(result.aggregate_drawdown, 0.0)
        self.assertEqual(result.aggregate_risk_score, 0.0)

    def test_engine_ignora_alpha_sem_drawdown_reportado(self) -> None:
        weights = AllocationWeightResult(
            equal_weight={"Alpha999": 0.5},
            risk_adjusted_weight={"Alpha999": 0.5},
        )

        result = AllocationRiskEngine().calculate(weights, self._report())

        self.assertEqual(result.portfolio_exposure, 0.5)
        self.assertEqual(result.concentration_score, 0.5)
        self.assertEqual(result.aggregate_drawdown, 0.0)
        self.assertEqual(result.aggregate_risk_score, 1.0)

    def test_engine_nao_modifica_pesos(self) -> None:
        weights = self._weights()

        AllocationRiskEngine().calculate(weights, self._report())

        self.assertEqual(weights.risk_adjusted_weight, {"Alpha001": 0.4, "Alpha002": 0.2})

    def test_engine_nao_recalcula_metricas_das_alphas(self) -> None:
        report = self._report()

        AllocationRiskEngine().calculate(self._weights(), report)

        self.assertEqual(report.comparison_result.comparisons[0].max_drawdown, 3.0)
        self.assertEqual(report.comparison_result.comparisons[1].max_drawdown, 3.0)

    def test_result_e_imutavel(self) -> None:
        result = AllocationRiskEngine().calculate(self._weights(), self._report())

        with self.assertRaises(FrozenInstanceError):
            result.aggregate_risk_score = 0.0

    def test_engine_nao_acessa_risk_engine_operacional_ou_camadas(self) -> None:
        source = read_source(Path("research/portfolio/allocation_risk_engine.py"))
        forbidden_fragments = (
            "risk.risk_engine",
            "RiskPipeline",
            "RiskPolicyEngine",
            "ResearchRunner",
            "ResearchPipeline",
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
            ".compare(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/allocation_risk_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "risk",
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
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _weights(self) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha001": 0.3, "Alpha002": 0.3},
            risk_adjusted_weight={"Alpha001": 0.4, "Alpha002": 0.2},
        )

    def _report(self) -> PortfolioResearchReport:
        return PortfolioResearchReport(
            alpha_registry=AlphaRegistry(),
            alpha_profiles=(
                self._profile_for("Alpha001"),
                self._profile_for("Alpha002"),
            ),
            comparison_result=PortfolioComparisonResult(
                total_results=2,
                comparisons=(
                    self._comparison("Alpha001", max_drawdown=3.0),
                    self._comparison("Alpha002", max_drawdown=3.0),
                ),
            ),
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
        max_drawdown: float,
    ) -> PortfolioResearchComparison:
        return PortfolioResearchComparison(
            alpha_id=alpha_id,
            total_trades=10,
            net_profit=100.0,
            max_drawdown=max_drawdown,
            profit_factor=2.0,
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
