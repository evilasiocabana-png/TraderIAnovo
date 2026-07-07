"""Testes do relatorio oficial da pesquisa de alocacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.allocation_profile import AllocationProfile
from research.portfolio.allocation_report import AllocationReport
from research.portfolio.allocation_risk_engine import AllocationRiskResult
from research.portfolio.allocation_simulation import AllocationSimulationResult
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AllocationReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou geracao de saida."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationReport))
        self.assertTrue(AllocationReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AllocationReport)]

        self.assertEqual(
            field_names,
            [
                "profile",
                "weights",
                "risk",
                "simulation",
                "allocation_method",
                "alpha_weights",
                "portfolio_return",
                "aggregate_drawdown",
                "aggregate_risk_score",
                "portfolio_equity_curve",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = AllocationReport.__annotations__

        self.assertEqual(annotations["profile"], "AllocationProfile")
        self.assertEqual(annotations["weights"], "AllocationWeightResult")
        self.assertEqual(annotations["risk"], "AllocationRiskResult")
        self.assertEqual(annotations["simulation"], "AllocationSimulationResult")
        self.assertEqual(annotations["allocation_method"], "str")
        self.assertEqual(annotations["alpha_weights"], "Mapping[str, float]")
        self.assertEqual(annotations["portfolio_return"], "float")
        self.assertEqual(annotations["aggregate_drawdown"], "float")
        self.assertEqual(annotations["aggregate_risk_score"], "float")
        self.assertEqual(annotations["portfolio_equity_curve"], "tuple[float, ...]")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.profile, AllocationProfile)
        self.assertIsInstance(report.weights, AllocationWeightResult)
        self.assertIsInstance(report.risk, AllocationRiskResult)
        self.assertIsInstance(report.simulation, AllocationSimulationResult)
        self.assertEqual(report.allocation_method, "RISK_ADJUSTED")
        self.assertEqual(report.alpha_weights, {"Alpha001": 0.4, "Alpha002": 0.2})
        self.assertEqual(report.portfolio_return, 8.0)
        self.assertEqual(report.aggregate_drawdown, 1.8)
        self.assertEqual(report.aggregate_risk_score, 2.8)
        self.assertEqual(report.portfolio_equity_curve, (0.0, 3.0, 8.0))
        self.assertEqual(report.execution_time, 2.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        profile = self._profile()
        weights = self._weights()
        risk = self._risk()
        simulation = self._simulation()
        metadata = {"source": "unit-test"}

        report = AllocationReport(
            profile=profile,
            weights=weights,
            risk=risk,
            simulation=simulation,
            allocation_method=profile.allocation_method,
            alpha_weights=weights.risk_adjusted_weight,
            portfolio_return=simulation.portfolio_return,
            aggregate_drawdown=risk.aggregate_drawdown,
            aggregate_risk_score=risk.aggregate_risk_score,
            portfolio_equity_curve=simulation.portfolio_equity_curve,
            execution_time=2.5,
            metadata=metadata,
        )

        self.assertIs(report.profile, profile)
        self.assertIs(report.weights, weights)
        self.assertIs(report.risk, risk)
        self.assertIs(report.simulation, simulation)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.portfolio_return = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/portfolio/allocation_report.py"))
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
            "PortfolioResearchComparator",
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
        path = Path("research/portfolio/allocation_report.py")
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

    def _report(self) -> AllocationReport:
        profile = self._profile()
        weights = self._weights()
        risk = self._risk()
        simulation = self._simulation()
        return AllocationReport(
            profile=profile,
            weights=weights,
            risk=risk,
            simulation=simulation,
            allocation_method=profile.allocation_method,
            alpha_weights=weights.risk_adjusted_weight,
            portfolio_return=simulation.portfolio_return,
            aggregate_drawdown=risk.aggregate_drawdown,
            aggregate_risk_score=risk.aggregate_risk_score,
            portfolio_equity_curve=simulation.portfolio_equity_curve,
            execution_time=2.5,
            metadata={"source": "unit-test"},
        )

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
            created_at="2026-06-28T01:40:00-03:00",
            metadata={"source": "unit-test"},
        )

    def _weights(self) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha001": 0.3, "Alpha002": 0.3},
            risk_adjusted_weight={"Alpha001": 0.4, "Alpha002": 0.2},
        )

    def _risk(self) -> AllocationRiskResult:
        return AllocationRiskResult(
            portfolio_exposure=0.6,
            concentration_score=0.4,
            aggregate_drawdown=1.8,
            aggregate_risk_score=2.8,
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
