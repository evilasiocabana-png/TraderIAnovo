"""Testes do engine de risco agregado do portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_risk_engine import AllocationRiskResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.portfolio.portfolio_risk_engine import (
    PortfolioRiskEngine,
    PortfolioRiskResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioRiskEngineTest(unittest.TestCase):
    """Valida risco agregado sem recalcular risco individual."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioRiskResult))
        self.assertTrue(PortfolioRiskResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioRiskResult)],
            [
                "aggregate_risk",
                "aggregate_drawdown",
                "concentration_score",
                "diversification_score",
            ],
        )

    def test_engine_consolida_risco_existente(self) -> None:
        result = PortfolioRiskEngine().evaluate(
            optimization_result=self._optimization_result(),
            allocation_risk=self._allocation_risk(),
        )

        self.assertEqual(result.aggregate_risk, 2.8)
        self.assertEqual(result.aggregate_drawdown, 1.8)
        self.assertEqual(result.concentration_score, 0.4)
        self.assertEqual(result.diversification_score, 0.6)

    def test_engine_retorna_diversificacao_zero_sem_pesos(self) -> None:
        result = PortfolioRiskEngine().evaluate(
            optimization_result=self._optimization_result(selected_weights={}),
            allocation_risk=self._allocation_risk(),
        )

        self.assertEqual(result.diversification_score, 0.0)

    def test_result_e_imutavel(self) -> None:
        result = PortfolioRiskEngine().evaluate(
            optimization_result=self._optimization_result(),
            allocation_risk=self._allocation_risk(),
        )

        with self.assertRaises(FrozenInstanceError):
            result.aggregate_risk = 0.0

    def test_engine_nao_recalcula_risco_individual_ou_altera_allocation_engine(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_risk_engine.py"))
        forbidden_fragments = (
            "AllocationRiskEngine",
            "ResearchPipeline",
            "ResearchRunner",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".calculate(",
            ".compare(",
            ".run(",
            "portfolio_exposure",
            "max_drawdown",
            "profit_factor",
            "win_rate",
            "expectancy",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_risk_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "risk",
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
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _optimization_result(
        self,
        selected_weights: dict[str, float] | None = None,
    ) -> PortfolioOptimizationResult:
        return PortfolioOptimizationResult(
            profile_id="portfolio-optimization-001",
            optimization_goal="BALANCED",
            allocation_method="RISK_ADJUSTED",
            selected_weights=selected_weights
            if selected_weights is not None
            else {"Alpha001": 0.4, "Alpha301": 0.2},
            equal_weight={"Alpha001": 0.3, "Alpha301": 0.3},
            risk_adjusted_weight={"Alpha001": 0.4, "Alpha301": 0.2},
            benchmark_recommendation="KEEP_BOTH_FOR_RESEARCH",
            execution_time=1.5,
            metadata={},
        )

    def _allocation_risk(self) -> AllocationRiskResult:
        return AllocationRiskResult(
            portfolio_exposure=0.6,
            concentration_score=0.4,
            aggregate_drawdown=1.8,
            aggregate_risk_score=2.8,
        )


if __name__ == "__main__":
    unittest.main()
