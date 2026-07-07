"""Contratos do orcamento de performance da suite de testes."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import test_performance_budget


class TestPerformanceBudgetTest(unittest.TestCase):
    """Valida o script de budget sem executar suites reais."""

    def _create_test_files(self, folder: Path, names: list[str]) -> None:
        for name in names:
            (folder / name).write_text(
                "import unittest\n\n"
                "class SampleTest(unittest.TestCase):\n"
                "    def test_sample(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

    def _runner(
        self,
        durations: dict[str, float],
        exit_codes: dict[str, int] | None = None,
    ):
        codes = exit_codes or {}

        def run(path: Path) -> test_performance_budget.SuiteTiming:
            return test_performance_budget.SuiteTiming(
                file=f"tests/{path.name}",
                duration_seconds=durations[path.name],
                exit_code=codes.get(path.name, 0),
            )

        return run

    def test_script_gera_relatorio_json_valido(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir()
            self._create_test_files(tests_dir, ["test_fast.py", "test_slow.py"])
            report_path = Path(temp_dir) / "test_performance_budget.json"

            report = test_performance_budget.run_budget(
                tests_dir=tests_dir,
                report_path=report_path,
                runner=self._runner(
                    {
                        "test_fast.py": 0.1,
                        "test_slow.py": 0.2,
                    }
                ),
                previous_report={},
            )
            loaded = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(loaded["summary"]["total_suites"], 2)
        self.assertEqual(loaded["summary"]["total_duration_seconds"], 0.3)
        self.assertEqual(len(loaded["suites"]), 2)

    def test_limites_de_aviso_sao_aplicados_sem_falhar_status(self) -> None:
        timing = test_performance_budget.SuiteTiming(
            file="tests/test_slow.py",
            duration_seconds=test_performance_budget.WARNING_SUITE_SECONDS + 1,
            exit_code=0,
        )

        warnings, violations = test_performance_budget.evaluate_budget(
            [timing],
            timing.duration_seconds,
            previous_report=None,
        )

        self.assertEqual(violations, [])
        self.assertTrue(
            any(item.category == "slow_suite" for item in warnings),
        )

    def test_status_failed_quando_suite_falha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir()
            self._create_test_files(tests_dir, ["test_broken.py"])
            report = test_performance_budget.run_budget(
                tests_dir=tests_dir,
                report_path=Path(temp_dir) / "report.json",
                runner=self._runner(
                    {"test_broken.py": 0.1},
                    {"test_broken.py": 7},
                ),
                previous_report={},
            )

        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["violations"][0]["category"], "test_failure")

    def test_degradacao_extrema_calcula_status_failed(self) -> None:
        previous = {"summary": {"total_duration_seconds": 100.0}}
        timings = [
            test_performance_budget.SuiteTiming(
                file="tests/test_large.py",
                duration_seconds=250.0,
                exit_code=0,
            )
        ]

        warnings, violations = test_performance_budget.evaluate_budget(
            timings,
            total_duration=250.0,
            previous_report=previous,
        )
        report = test_performance_budget.build_report(
            timings,
            total_duration=250.0,
            warnings=warnings,
            violations=violations,
            status="FAILED" if violations else "PASSED",
            previous_report=previous,
        )

        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(
            any(item["category"] == "trend" for item in report["violations"]),
        )
        self.assertEqual(report["summary"]["trend"]["ratio"], 2.5)


if __name__ == "__main__":
    unittest.main()
