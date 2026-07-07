"""Testes do relatorio oficial da validacao Monte Carlo."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.monte_carlo.monte_carlo_analyzer import (
    MonteCarloAnalysisResult,
)
from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from research.validation.monte_carlo.monte_carlo_report import MonteCarloReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MonteCarloReportTest(unittest.TestCase):
    """Valida relatorio puro de validacao Monte Carlo."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloReport))
        self.assertTrue(MonteCarloReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(MonteCarloReport)],
            [
                "monte_carlo_result",
                "analysis_result",
                "simulations",
                "confidence_level",
                "average_return",
                "worst_case_return",
                "best_case_return",
                "expected_drawdown",
                "robustness_score",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = MonteCarloReport.__annotations__

        self.assertEqual(annotations["monte_carlo_result"], "MonteCarloResult")
        self.assertEqual(annotations["analysis_result"], "MonteCarloAnalysisResult")
        self.assertEqual(annotations["simulations"], "int")
        self.assertEqual(annotations["confidence_level"], "float")
        self.assertEqual(annotations["average_return"], "float")
        self.assertEqual(annotations["worst_case_return"], "float")
        self.assertEqual(annotations["best_case_return"], "float")
        self.assertEqual(annotations["expected_drawdown"], "float")
        self.assertEqual(annotations["robustness_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_resultados_anteriores(self) -> None:
        monte_carlo = self._monte_carlo_result()
        analysis = self._analysis_result()

        report = MonteCarloReport(
            monte_carlo_result=monte_carlo,
            analysis_result=analysis,
            simulations=monte_carlo.total_simulations,
            confidence_level=monte_carlo.confidence_level,
            average_return=analysis.average_return,
            worst_case_return=analysis.worst_case_return,
            best_case_return=analysis.best_case_return,
            expected_drawdown=analysis.expected_drawdown,
            robustness_score=analysis.robustness_score,
            execution_time=1.75,
            metadata={"source": "unit-test"},
        )

        self.assertIs(report.monte_carlo_result, monte_carlo)
        self.assertIs(report.analysis_result, analysis)
        self.assertEqual(report.simulations, 3)
        self.assertEqual(report.confidence_level, 0.95)
        self.assertEqual(report.average_return, 10.0)
        self.assertEqual(report.worst_case_return, -5.0)
        self.assertEqual(report.best_case_return, 20.0)
        self.assertEqual(report.expected_drawdown, 3.0)
        self.assertEqual(report.robustness_score, 0.7)
        self.assertEqual(report.execution_time, 1.75)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_e_imutavel(self) -> None:
        report = MonteCarloReport(
            monte_carlo_result=self._monte_carlo_result(),
            analysis_result=self._analysis_result(),
            simulations=3,
            confidence_level=0.95,
            average_return=10.0,
            worst_case_return=-5.0,
            best_case_return=20.0,
            expected_drawdown=3.0,
            robustness_score=0.7,
            execution_time=1.75,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.robustness_score = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(
            Path("research/validation/monte_carlo/monte_carlo_report.py")
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
            ".run(",
            ".calculate(",
            ".analyze(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/validation/monte_carlo/monte_carlo_report.py")
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
            "analyze",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _monte_carlo_result(self) -> MonteCarloResult:
        return MonteCarloResult(
            campaign_id="campaign-alpha001-mc",
            profile=self._profile(),
            executed_experiments=(self._experiment(),),
            total_simulations=3,
            simulated_returns=(10.0, 20.0, -5.0),
            simulated_drawdowns=(2.0, 3.0, 4.0),
            average_return=25.0 / 3.0,
            worst_return=-5.0,
            best_return=20.0,
            confidence_level=0.95,
        )

    def _analysis_result(self) -> MonteCarloAnalysisResult:
        return MonteCarloAnalysisResult(
            average_return=10.0,
            worst_case_return=-5.0,
            best_case_return=20.0,
            expected_drawdown=3.0,
            robustness_score=0.7,
        )

    def _profile(self) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=3,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="REORDER_TRADES",
            metadata={},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-mc",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T07:10:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
