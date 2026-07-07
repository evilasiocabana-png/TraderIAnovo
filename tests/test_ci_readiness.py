"""Contratos da validacao de prontidao para CI."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import ci_readiness


class CiReadinessTest(unittest.TestCase):
    """Valida readiness sem executar comandos reais."""

    def _runner(self, exit_code: int = 0):
        def run(name: str, command: tuple[str, ...]) -> ci_readiness.CommandResult:
            return ci_readiness.CommandResult(
                name=name,
                command=" ".join(command),
                exit_code=exit_code,
                duration_seconds=0.01,
                stdout_tail="ok",
                stderr_tail="",
            )

        return run

    def test_relatorio_eh_gerado_com_json_valido(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "ci_readiness.json"
            with (
                patch("scripts.ci_readiness.check_environment", return_value=[]),
                patch("scripts.ci_readiness.check_dependencies", return_value=[]),
                patch("scripts.ci_readiness.check_structure", return_value=[]),
                patch(
                    "scripts.ci_readiness.check_reports_write_permission",
                    return_value=ci_readiness.CheckResult(
                        "reports_write_permission",
                        "PASSED",
                        "ok",
                    ),
                ),
                patch("scripts.ci_readiness.scan_sources_for_ci_risks", return_value=[]),
                patch("scripts.ci_readiness.check_report_consistency", return_value=[]),
            ):
                report = ci_readiness.run_readiness(
                    runner=self._runner(),
                    report_path=report_path,
                )
            loaded = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "READY")
        self.assertEqual(loaded["status"], "READY")
        self.assertEqual(len(loaded["commands"]), len(ci_readiness.COMMANDS))

    def test_classificacao_ready_with_warnings(self) -> None:
        status = ci_readiness.classify_status(
            problems=[],
            warnings=[
                ci_readiness.CheckResult(
                    "absolute_user_path",
                    "WARNING",
                    "warning",
                    severity="warning",
                )
            ],
        )

        self.assertEqual(status, "READY WITH WARNINGS")

    def test_classificacao_not_ready_com_problemas(self) -> None:
        status = ci_readiness.classify_status(
            problems=[
                ci_readiness.CheckResult(
                    "dependency:streamlit",
                    "FAILED",
                    "missing",
                    severity="error",
                )
            ],
            warnings=[],
        )

        self.assertEqual(status, "NOT READY")

    def test_comando_com_falha_vira_problema(self) -> None:
        command_results = [
            ci_readiness.CommandResult(
                name="test_suite",
                command="python -m unittest",
                exit_code=3,
                duration_seconds=0.1,
            )
        ]

        checks = ci_readiness.checks_from_commands(command_results)

        self.assertEqual(checks[0].severity, "error")
        self.assertEqual(checks[0].status, "FAILED")

    def test_validacao_nao_modifica_aplicacao(self) -> None:
        app_path = Path("app.py")
        before = app_path.read_text(encoding="utf-8")

        with (
            patch("scripts.ci_readiness.check_environment", return_value=[]),
            patch("scripts.ci_readiness.check_dependencies", return_value=[]),
            patch("scripts.ci_readiness.check_structure", return_value=[]),
            patch(
                "scripts.ci_readiness.check_reports_write_permission",
                return_value=ci_readiness.CheckResult(
                    "reports_write_permission",
                    "PASSED",
                    "ok",
                ),
            ),
            patch("scripts.ci_readiness.scan_sources_for_ci_risks", return_value=[]),
            patch("scripts.ci_readiness.check_report_consistency", return_value=[]),
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                ci_readiness.run_readiness(
                    runner=self._runner(),
                    report_path=Path(temp_dir) / "ci_readiness.json",
                )

        self.assertEqual(app_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
