"""Contratos do relatorio consolidado do quality gate."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_quality_gate


class QualityGateSummaryTest(unittest.TestCase):
    """Valida o relatorio executivo sem executar comandos reais."""

    def _result(
        self,
        step: run_quality_gate.QualityGateStep,
        exit_code: int,
        duration_seconds: float = 0.1,
    ) -> run_quality_gate.QualityGateStepResult:
        status = "PASSED" if exit_code == 0 else "FAILED"
        return run_quality_gate.QualityGateStepResult(
            step=step,
            status=status,
            duration_seconds=duration_seconds,
            exit_code=exit_code,
            message=f"{step.name} status {status}.",
        )

    def test_relatorio_eh_gerado_com_json_valido(self) -> None:
        results = [
            self._result(step, 0)
            for step in run_quality_gate.QUALITY_GATE_STEPS
        ]
        summary = run_quality_gate.build_summary(
            results,
            executed_at="2026-06-27T10:00:00-03:00",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "quality_gate_summary.json"
            run_quality_gate.write_summary(summary, report_path)
            loaded = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(loaded["executed_at"], "2026-06-27T10:00:00-03:00")
        self.assertEqual(loaded["overall_status"], "PASSED")
        self.assertEqual(
            set(loaded["steps"]),
            {"static_analysis", "app_py", "test_suite", "architecture_audit"},
        )

    def test_status_geral_passed_quando_todas_etapas_passam(self) -> None:
        summary = run_quality_gate.build_summary(
            [
                self._result(step, 0)
                for step in run_quality_gate.QUALITY_GATE_STEPS
            ]
        )

        self.assertEqual(summary["overall_status"], "PASSED")

    def test_falha_individual_propaga_status_failed(self) -> None:
        steps = run_quality_gate.QUALITY_GATE_STEPS
        summary = run_quality_gate.build_summary(
            [
                self._result(steps[0], 0),
                self._result(steps[1], 13),
            ]
        )

        self.assertEqual(summary["overall_status"], "FAILED")
        self.assertEqual(summary["steps"]["app_py"]["status"], "FAILED")
        self.assertEqual(summary["steps"]["test_suite"]["status"], "NOT_RUN")
        self.assertEqual(summary["steps"]["architecture_audit"]["status"], "NOT_RUN")

    def test_exit_codes_sao_registrados(self) -> None:
        steps = run_quality_gate.QUALITY_GATE_STEPS
        summary = run_quality_gate.build_summary(
            [
                self._result(steps[0], 0),
                self._result(steps[1], 7),
            ]
        )

        self.assertEqual(summary["steps"]["static_analysis"]["exit_code"], 0)
        self.assertEqual(summary["steps"]["app_py"]["exit_code"], 7)
        self.assertIsNone(summary["steps"]["test_suite"]["exit_code"])

    def test_main_gera_relatorio_e_preserva_exit_code_da_primeira_falha(self) -> None:
        results = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=5),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "quality_gate_summary.json"
            with (
                patch("scripts.run_quality_gate.REPORT_PATH", report_path),
                patch(
                    "scripts.run_quality_gate.subprocess.run",
                    side_effect=results,
                ),
                patch("scripts.run_quality_gate._register_history"),
                patch("scripts.run_quality_gate.print"),
            ):
                exit_code = run_quality_gate.main()

            loaded = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 5)
        self.assertEqual(loaded["overall_status"], "FAILED")
        self.assertEqual(loaded["steps"]["app_py"]["exit_code"], 5)


if __name__ == "__main__":
    unittest.main()
