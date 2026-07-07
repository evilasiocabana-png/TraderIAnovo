"""Contratos do diagnostico estruturado de falhas de testes."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import test_failure_diagnostics


class TestFailureDiagnosticsTest(unittest.TestCase):
    """Valida diagnostico sem executar a suite real."""

    def _runner(
        self,
        *,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ):
        def run() -> test_failure_diagnostics.TestRunResult:
            return test_failure_diagnostics.TestRunResult(
                command=["python", "-m", "unittest", "discover", "-s", "tests"],
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )

        return run

    def test_script_gera_relatorio_json_valido(self) -> None:
        output = "...\n----------------------------------------------------------------------\nRan 3 tests in 0.001s\n\nOK\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "diagnostics.json"
            report = test_failure_diagnostics.run_diagnostics(
                runner=self._runner(returncode=0, stderr=output),
                report_path=report_path,
            )
            loaded = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(loaded["summary"]["total_tests"], 3)
        self.assertEqual(loaded["failures_by_category"], {})

    def test_falhas_sao_categorizadas_por_area(self) -> None:
        output = """
======================================================================
FAIL: test_replay_pipeline (tests.test_replay_service.ReplayServiceTest.test_replay_pipeline)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\\repo\\tests\\test_replay_service.py", line 10, in test_replay_pipeline
    self.assertEqual("RUNNING", status)
AssertionError: 'RUNNING' != 'STOPPED'

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (failures=1)
"""

        report = test_failure_diagnostics.build_report(
            test_failure_diagnostics.TestRunResult(
                command=["python", "-m", "unittest"],
                returncode=1,
                stdout="",
                stderr=output,
            )
        )

        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["summary"]["failures"], 1)
        self.assertIn("replay", report["failures_by_category"])
        self.assertEqual(
            report["failures_by_category"]["replay"][0]["file"],
            "tests/test_replay_service.py",
        )

    def test_erros_de_import_sao_categorizados(self) -> None:
        output = """
======================================================================
ERROR: tests.test_dashboard_app_runtime (unittest.loader._FailedTest.tests.test_dashboard_app_runtime)
----------------------------------------------------------------------
ImportError: Failed to import test module: tests.test_dashboard_app_runtime
Traceback (most recent call last):
  File "C:\\Python\\Lib\\unittest\\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
ModuleNotFoundError: No module named 'streamlit'

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
"""

        failures = test_failure_diagnostics.parse_failures(output)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["category"], "import")
        self.assertIn("ModuleNotFoundError", failures[0]["message"])

    def test_execucao_sem_falhas_nao_cria_efeitos_colaterais_fora_do_relatorio(self) -> None:
        output = ".\n----------------------------------------------------------------------\nRan 1 test in 0.001s\n\nOK\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "diagnostics.json"
            test_failure_diagnostics.run_diagnostics(
                runner=self._runner(returncode=0, stderr=output),
                report_path=report_path,
            )
            generated = sorted(path.name for path in Path(temp_dir).iterdir())

        self.assertEqual(generated, ["diagnostics.json"])


if __name__ == "__main__":
    unittest.main()
