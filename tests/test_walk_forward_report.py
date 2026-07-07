"""Testes do relatorio oficial Walk-Forward."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.walk_forward_analyzer import WalkForwardAnalysisResult
from research.validation.walk_forward_engine import WalkForwardResult
from research.validation.walk_forward_profile import WalkForwardProfile
from research.validation.walk_forward_report import WalkForwardReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class WalkForwardReportTest(unittest.TestCase):
    """Valida relatorio puro de validacao Walk-Forward."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardReport))
        self.assertTrue(WalkForwardReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(WalkForwardReport)],
            [
                "walk_forward_result",
                "analysis_result",
                "training_summary",
                "validation_summary",
                "testing_summary",
                "degradation_score",
                "stability_score",
                "consistency_score",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = WalkForwardReport.__annotations__

        self.assertEqual(annotations["walk_forward_result"], "WalkForwardResult")
        self.assertEqual(annotations["analysis_result"], "WalkForwardAnalysisResult")
        self.assertEqual(annotations["training_summary"], "str")
        self.assertEqual(annotations["validation_summary"], "str")
        self.assertEqual(annotations["testing_summary"], "str")
        self.assertEqual(annotations["degradation_score"], "float")
        self.assertEqual(annotations["stability_score"], "float")
        self.assertEqual(annotations["consistency_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_resultados_anteriores(self) -> None:
        walk_forward = self._walk_forward_result()
        analysis = self._analysis_result()

        report = WalkForwardReport(
            walk_forward_result=walk_forward,
            analysis_result=analysis,
            training_summary="Treino completo.",
            validation_summary="Validacao completa.",
            testing_summary="Teste completo.",
            degradation_score=analysis.degradation_score,
            stability_score=analysis.stability_score,
            consistency_score=analysis.consistency_score,
            execution_time=2.5,
            metadata={"source": "unit-test"},
        )

        self.assertIs(report.walk_forward_result, walk_forward)
        self.assertIs(report.analysis_result, analysis)
        self.assertEqual(report.training_summary, "Treino completo.")
        self.assertEqual(report.validation_summary, "Validacao completa.")
        self.assertEqual(report.testing_summary, "Teste completo.")
        self.assertEqual(report.degradation_score, 0.1)
        self.assertEqual(report.stability_score, 0.9)
        self.assertEqual(report.consistency_score, 0.8)
        self.assertEqual(report.execution_time, 2.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_e_imutavel(self) -> None:
        report = WalkForwardReport(
            walk_forward_result=self._walk_forward_result(),
            analysis_result=self._analysis_result(),
            training_summary="Treino.",
            validation_summary="Validacao.",
            testing_summary="Teste.",
            degradation_score=0.1,
            stability_score=0.9,
            consistency_score=0.8,
            execution_time=2.5,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.execution_time = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/validation/walk_forward_report.py"))
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
        path = Path("research/validation/walk_forward_report.py")
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

    def _walk_forward_result(self) -> WalkForwardResult:
        experiments = (self._experiment("exp-1"),)
        return WalkForwardResult(
            campaign_id="campaign-alpha001-wf",
            profile=self._profile(),
            executed_experiments=experiments,
            training_experiments=experiments,
            validation_experiments=(),
            testing_experiments=(),
            rolling_window=1,
            minimum_samples=100,
        )

    def _analysis_result(self) -> WalkForwardAnalysisResult:
        return WalkForwardAnalysisResult(
            stability_score=0.9,
            degradation_score=0.1,
            consistency_score=0.8,
            validation_score=0.85,
        )

    def _experiment(self, experiment_id: str) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T06:10:00-03:00",
            metadata={},
        )

    def _profile(self) -> WalkForwardProfile:
        return WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=2,
            validation_window=2,
            testing_window=1,
            rolling_window=1,
            minimum_samples=100,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
