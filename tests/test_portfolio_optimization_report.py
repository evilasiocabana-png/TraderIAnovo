"""Testes do relatorio oficial de otimizacao de portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_simulation import AllocationSimulationResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.portfolio.portfolio_optimization_report import (
    PortfolioOptimizationReport,
    PortfolioSimulationResult,
)
from research.portfolio.portfolio_risk_engine import PortfolioRiskResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioOptimizationReportTest(unittest.TestCase):
    """Valida relatorio puro da otimizacao de portfolio."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioOptimizationReport))
        self.assertTrue(PortfolioOptimizationReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioOptimizationReport)],
            [
                "optimization",
                "risk",
                "simulation",
                "optimization_goal",
                "allocation_method",
                "alpha_weights",
                "expected_return",
                "aggregate_drawdown",
                "diversification_score",
                "aggregate_risk",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = PortfolioOptimizationReport.__annotations__

        self.assertEqual(annotations["optimization"], "PortfolioOptimizationResult")
        self.assertEqual(annotations["risk"], "PortfolioRiskResult")
        self.assertEqual(annotations["simulation"], "PortfolioSimulationResult")
        self.assertEqual(annotations["optimization_goal"], "str")
        self.assertEqual(annotations["allocation_method"], "str")
        self.assertEqual(annotations["alpha_weights"], "Mapping[str, float]")
        self.assertEqual(annotations["expected_return"], "float")
        self.assertEqual(annotations["aggregate_drawdown"], "float")
        self.assertEqual(annotations["diversification_score"], "float")
        self.assertEqual(annotations["aggregate_risk"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_portfolio_simulation_result_reutiliza_allocation_simulation_result(self) -> None:
        self.assertIs(PortfolioSimulationResult, AllocationSimulationResult)

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.optimization, PortfolioOptimizationResult)
        self.assertIsInstance(report.risk, PortfolioRiskResult)
        self.assertIsInstance(report.simulation, AllocationSimulationResult)
        self.assertEqual(report.optimization_goal, "BALANCED")
        self.assertEqual(report.allocation_method, "RISK_ADJUSTED")
        self.assertEqual(report.alpha_weights, {"Alpha001": 0.4, "Alpha301": 0.2})
        self.assertEqual(report.expected_return, 8.0)
        self.assertEqual(report.aggregate_drawdown, 1.8)
        self.assertEqual(report.diversification_score, 0.6)
        self.assertEqual(report.aggregate_risk, 2.8)
        self.assertEqual(report.execution_time, 2.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        optimization = self._optimization()
        risk = self._risk()
        simulation = self._simulation()
        metadata = {"source": "unit-test"}

        report = PortfolioOptimizationReport(
            optimization=optimization,
            risk=risk,
            simulation=simulation,
            optimization_goal=optimization.optimization_goal,
            allocation_method=optimization.allocation_method,
            alpha_weights=optimization.selected_weights,
            expected_return=simulation.portfolio_return,
            aggregate_drawdown=risk.aggregate_drawdown,
            diversification_score=risk.diversification_score,
            aggregate_risk=risk.aggregate_risk,
            execution_time=2.5,
            metadata=metadata,
        )

        self.assertIs(report.optimization, optimization)
        self.assertIs(report.risk, risk)
        self.assertIs(report.simulation, simulation)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.expected_return = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_optimization_report.py")
        )
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "AllocationReport",
            "ResearchPipeline",
            "ResearchRunner",
            ".run(",
            ".execute(",
            ".calculate(",
            ".simulate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/portfolio_optimization_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.portfolio.allocation_report",
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
            "simulate",
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> PortfolioOptimizationReport:
        optimization = self._optimization()
        risk = self._risk()
        simulation = self._simulation()
        return PortfolioOptimizationReport(
            optimization=optimization,
            risk=risk,
            simulation=simulation,
            optimization_goal=optimization.optimization_goal,
            allocation_method=optimization.allocation_method,
            alpha_weights=optimization.selected_weights,
            expected_return=simulation.portfolio_return,
            aggregate_drawdown=risk.aggregate_drawdown,
            diversification_score=risk.diversification_score,
            aggregate_risk=risk.aggregate_risk,
            execution_time=2.5,
            metadata={"source": "unit-test"},
        )

    def _optimization(self) -> PortfolioOptimizationResult:
        return PortfolioOptimizationResult(
            profile_id="portfolio-optimization-001",
            optimization_goal="BALANCED",
            allocation_method="RISK_ADJUSTED",
            selected_weights={"Alpha001": 0.4, "Alpha301": 0.2},
            equal_weight={"Alpha001": 0.3, "Alpha301": 0.3},
            risk_adjusted_weight={"Alpha001": 0.4, "Alpha301": 0.2},
            benchmark_recommendation="KEEP_BOTH_FOR_RESEARCH",
            execution_time=1.5,
            metadata={},
        )

    def _risk(self) -> PortfolioRiskResult:
        return PortfolioRiskResult(
            aggregate_risk=2.8,
            aggregate_drawdown=1.8,
            concentration_score=0.4,
            diversification_score=0.6,
        )

    def _simulation(self) -> AllocationSimulationResult:
        return AllocationSimulationResult(
            portfolio_equity_curve=(0.0, 3.0, 8.0),
            portfolio_return=8.0,
            portfolio_drawdown=0.0,
            portfolio_volatility=2.0,
        )


if __name__ == "__main__":
    unittest.main()
