"""Testes do relatorio oficial de ciclo de vida de Alphas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha_factory.alpha_deprecation_engine import AlphaDeprecationResult
from research.alpha_factory.alpha_health_engine import AlphaHealthResult
from research.alpha_factory.alpha_lifecycle import (
    AlphaLifecycle,
    AlphaLifecycleStatus,
)
from research.alpha_factory.alpha_lifecycle_report import AlphaLifecycleReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaLifecycleReportTest(unittest.TestCase):
    """Valida consolidacao pura do ciclo de vida de Alphas."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaLifecycleReport))
        self.assertTrue(AlphaLifecycleReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaLifecycleReport)],
            [
                "lifecycle",
                "health_result",
                "deprecation_result",
                "alpha_id",
                "lifecycle_status",
                "health_score",
                "robustness_score",
                "reproducibility_score",
                "recommendation",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.lifecycle, AlphaLifecycle)
        self.assertIsInstance(report.health_result, AlphaHealthResult)
        self.assertIsInstance(report.deprecation_result, AlphaDeprecationResult)

    def test_report_apresenta_campos_consolidados(self) -> None:
        report = self._report()

        self.assertEqual(report.alpha_id, "Alpha003")
        self.assertEqual(report.lifecycle_status, "VALIDATION")
        self.assertEqual(report.health_score, 0.72)
        self.assertEqual(report.robustness_score, 0.75)
        self.assertEqual(report.reproducibility_score, 0.70)
        self.assertEqual(report.recommendation, "WATCH")
        self.assertEqual(report.execution_time, 3.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        lifecycle = self._lifecycle()
        health_result = self._health_result()
        deprecation_result = self._deprecation_result()
        metadata = {"source": "unit-test"}

        report = AlphaLifecycleReport(
            lifecycle=lifecycle,
            health_result=health_result,
            deprecation_result=deprecation_result,
            alpha_id=lifecycle.alpha_id,
            lifecycle_status=lifecycle.current_status.value,
            health_score=health_result.health_score,
            robustness_score=health_result.robustness_score,
            reproducibility_score=health_result.reproducibility_score,
            recommendation=deprecation_result.decision,
            execution_time=3.5,
            metadata=metadata,
        )

        self.assertIs(report.lifecycle, lifecycle)
        self.assertIs(report.health_result, health_result)
        self.assertIs(report.deprecation_result, deprecation_result)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.recommendation = "KEEP"

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_lifecycle_report.py")
        )
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            " / ",
            " * ",
            " + ",
            " - ",
            ".run(",
            ".evaluate(",
            ".calculate(",
            ".validate(",
            ".transition(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_lifecycle_report.py")
        )
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
            "persist",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_lifecycle_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "evaluate",
            "calculate",
            "validate",
            "transition",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> AlphaLifecycleReport:
        lifecycle = self._lifecycle()
        health_result = self._health_result()
        deprecation_result = self._deprecation_result()
        return AlphaLifecycleReport(
            lifecycle=lifecycle,
            health_result=health_result,
            deprecation_result=deprecation_result,
            alpha_id=lifecycle.alpha_id,
            lifecycle_status=lifecycle.current_status.value,
            health_score=health_result.health_score,
            robustness_score=health_result.robustness_score,
            reproducibility_score=health_result.reproducibility_score,
            recommendation=deprecation_result.decision,
            execution_time=3.5,
            metadata={"source": "unit-test"},
        )

    def _lifecycle(self) -> AlphaLifecycle:
        return AlphaLifecycle(
            alpha_id="Alpha003",
            current_status=AlphaLifecycleStatus.VALIDATION,
            previous_status=AlphaLifecycleStatus.RESEARCH,
            created_at=datetime(2026, 6, 28, 10, 0, 0),
            updated_at=datetime(2026, 6, 28, 11, 0, 0),
            metadata={},
        )

    def _health_result(self) -> AlphaHealthResult:
        return AlphaHealthResult(
            robustness_score=0.75,
            reproducibility_score=0.70,
            validation_score=0.68,
            campaign_score=0.75,
            health_score=0.72,
        )

    def _deprecation_result(self) -> AlphaDeprecationResult:
        return AlphaDeprecationResult(
            decision="WATCH",
            reasons=("Saude geral abaixo do limite de manutencao.",),
            keep_threshold=0.70,
            watch_threshold=0.40,
            deprecate_threshold=0.30,
        )


if __name__ == "__main__":
    unittest.main()
