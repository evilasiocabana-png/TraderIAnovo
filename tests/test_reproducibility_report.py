"""Testes do relatorio oficial de reprodutibilidade."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.reproducibility.experiment_fingerprint import (
    ExperimentFingerprint,
    ExperimentFingerprintResult,
)
from research.reproducibility.reproducibility_report import ReproducibilityReport
from research.reproducibility.reproducibility_validator import (
    ReproducibilityValidationResult,
    ReproducibilityValidator,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ReproducibilityReportTest(unittest.TestCase):
    """Valida agregacao pura dos componentes de reprodutibilidade."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ReproducibilityReport))
        self.assertTrue(ReproducibilityReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ReproducibilityReport)]

        self.assertEqual(
            field_names,
            [
                "snapshot",
                "fingerprint_result",
                "validation_result",
                "experiment_id",
                "fingerprint",
                "compatible_versions",
                "configuration_status",
                "dataset_status",
                "replay_status",
                "reproducibility_score",
                "execution_time",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = ReproducibilityReport.__annotations__

        self.assertEqual(annotations["snapshot"], "ResearchSnapshot")
        self.assertEqual(
            annotations["fingerprint_result"],
            "ExperimentFingerprintResult",
        )
        self.assertEqual(
            annotations["validation_result"],
            "ReproducibilityValidationResult",
        )
        self.assertEqual(annotations["experiment_id"], "str")
        self.assertEqual(annotations["fingerprint"], "str")
        self.assertEqual(annotations["compatible_versions"], "bool")
        self.assertEqual(annotations["configuration_status"], "str")
        self.assertEqual(annotations["dataset_status"], "str")
        self.assertEqual(annotations["replay_status"], "str")
        self.assertEqual(annotations["reproducibility_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.snapshot, ResearchSnapshot)
        self.assertIsInstance(report.fingerprint_result, ExperimentFingerprintResult)
        self.assertIsInstance(
            report.validation_result,
            ReproducibilityValidationResult,
        )
        self.assertEqual(report.experiment_id, "exp-alpha001-001")
        self.assertEqual(report.fingerprint, report.fingerprint_result.fingerprint)
        self.assertTrue(report.compatible_versions)
        self.assertEqual(report.configuration_status, "COMPATIBLE")
        self.assertEqual(report.dataset_status, "COMPATIBLE")
        self.assertEqual(report.replay_status, "COMPATIBLE")
        self.assertEqual(report.reproducibility_score, 1.0)
        self.assertEqual(report.execution_time, 2.5)

    def test_report_preserva_referencias_recebidas(self) -> None:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)
        validation = ReproducibilityValidator().validate(snapshot, fingerprint)

        report = ReproducibilityReport(
            snapshot=snapshot,
            fingerprint_result=fingerprint,
            validation_result=validation,
            experiment_id=snapshot.experiment_id,
            fingerprint=fingerprint.fingerprint,
            compatible_versions=True,
            configuration_status="COMPATIBLE",
            dataset_status="COMPATIBLE",
            replay_status="COMPATIBLE",
            reproducibility_score=1.0,
            execution_time=2.5,
        )

        self.assertIs(report.snapshot, snapshot)
        self.assertIs(report.fingerprint_result, fingerprint)
        self.assertIs(report.validation_result, validation)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.reproducibility_score = 0.0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/reproducibility/reproducibility_report.py"))
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
            ".run(",
            ".execute(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/reproducibility/reproducibility_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> ReproducibilityReport:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)
        validation = ReproducibilityValidator().validate(snapshot, fingerprint)
        return ReproducibilityReport(
            snapshot=snapshot,
            fingerprint_result=fingerprint,
            validation_result=validation,
            experiment_id=snapshot.experiment_id,
            fingerprint=fingerprint.fingerprint,
            compatible_versions=True,
            configuration_status="COMPATIBLE",
            dataset_status="COMPATIBLE",
            replay_status="COMPATIBLE",
            reproducibility_score=1.0,
            execution_time=2.5,
        )

    def _snapshot(self) -> ResearchSnapshot:
        return ResearchSnapshot(
            snapshot_id="snap-alpha001-001",
            experiment_id="exp-alpha001-001",
            alpha_id="Alpha001",
            alpha_version="1.0.0",
            configuration_version="cfg-001",
            feature_version="feat-001",
            context_version="ctx-001",
            risk_version="risk-001",
            research_pipeline_version="pipe-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            random_seed=42,
            created_at="2026-06-28T00:30:00-03:00",
            metadata={"parameters": {"stop": 50, "target": 100}},
        )


if __name__ == "__main__":
    unittest.main()
