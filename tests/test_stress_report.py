"""Testes do relatorio oficial da validacao sob estresse."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.stress.stress_analyzer import StressAnalysisResult
from research.validation.stress.stress_engine import StressResult
from research.validation.stress.stress_report import StressReport
from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StressReportTest(unittest.TestCase):
    """Valida relatorio puro de validacao sob estresse."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressReport))
        self.assertTrue(StressReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StressReport)],
            [
                "stress_result",
                "analysis_result",
                "scenario",
                "degradation_score",
                "recovery_score",
                "resilience_score",
                "stability_score",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = StressReport.__annotations__

        self.assertEqual(annotations["stress_result"], "StressResult")
        self.assertEqual(annotations["analysis_result"], "StressAnalysisResult")
        self.assertEqual(annotations["scenario"], "StressScenario")
        self.assertEqual(annotations["degradation_score"], "float")
        self.assertEqual(annotations["recovery_score"], "float")
        self.assertEqual(annotations["resilience_score"], "float")
        self.assertEqual(annotations["stability_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_resultados_anteriores(self) -> None:
        stress = self._stress_result()
        analysis = self._analysis_result()

        report = StressReport(
            stress_result=stress,
            analysis_result=analysis,
            scenario=stress.scenario,
            degradation_score=analysis.degradation_score,
            recovery_score=analysis.recovery_score,
            resilience_score=analysis.resilience_score,
            stability_score=analysis.stability_score,
            execution_time=1.25,
            metadata={"source": "unit-test"},
        )

        self.assertIs(report.stress_result, stress)
        self.assertIs(report.analysis_result, analysis)
        self.assertIs(report.scenario, stress.scenario)
        self.assertEqual(report.degradation_score, 0.2)
        self.assertEqual(report.recovery_score, 0.9)
        self.assertEqual(report.resilience_score, 0.85)
        self.assertEqual(report.stability_score, 0.95)
        self.assertEqual(report.execution_time, 1.25)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_e_imutavel(self) -> None:
        report = StressReport(
            stress_result=self._stress_result(),
            analysis_result=self._analysis_result(),
            scenario=self._scenario(),
            degradation_score=0.2,
            recovery_score=0.9,
            resilience_score=0.85,
            stability_score=0.95,
            execution_time=1.25,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.resilience_score = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/validation/stress/stress_report.py"))
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
        path = Path("research/validation/stress/stress_report.py")
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

    def _stress_result(self) -> StressResult:
        return StressResult(
            campaign_id="campaign-alpha001-stress",
            scenario=self._scenario(),
            executed_experiments=(self._experiment(),),
            total_experiments=1,
            scenario_enabled=True,
            status="COMPLETED",
        )

    def _analysis_result(self) -> StressAnalysisResult:
        return StressAnalysisResult(
            degradation_score=0.2,
            recovery_score=0.9,
            resilience_score=0.85,
            stability_score=0.95,
        )

    def _scenario(self) -> StressScenario:
        return StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo de mercado.",
            severity=1.0,
            enabled=True,
            metadata={"scope": "validation"},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-stress",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T07:50:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
