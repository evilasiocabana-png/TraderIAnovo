"""Contratos do quality gate local."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from scripts import run_quality_gate


class QualityGateTest(unittest.TestCase):
    """Valida o ponto unico de execucao local sem rodar comandos reais."""

    def test_quality_gate_define_etapas_obrigatorias(self) -> None:
        commands = [step.command for step in run_quality_gate.QUALITY_GATE_STEPS]

        self.assertEqual(
            commands,
            [
                (
                    run_quality_gate.sys.executable,
                    "scripts/run_static_analysis.py",
                ),
                (run_quality_gate.sys.executable, "app.py"),
                (
                    run_quality_gate.sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                ),
                (
                    run_quality_gate.sys.executable,
                    "scripts/architecture_audit.py",
                ),
            ],
        )

    def test_quality_gate_inclui_analise_estatica(self) -> None:
        commands = [step.command for step in run_quality_gate.QUALITY_GATE_STEPS]

        self.assertTrue(
            any("scripts/run_static_analysis.py" in command for command in commands),
            "Quality gate deve executar scripts/run_static_analysis.py.",
        )

    def test_quality_gate_inclui_auditoria_arquitetural(self) -> None:
        commands = [step.command for step in run_quality_gate.QUALITY_GATE_STEPS]

        self.assertTrue(
            any("scripts/architecture_audit.py" in command for command in commands),
            "Quality gate deve executar scripts/architecture_audit.py.",
        )

    def test_quality_gate_retorna_zero_quando_todas_etapas_passam(self) -> None:
        with (
            patch(
                "scripts.run_quality_gate.subprocess.run",
                return_value=subprocess.CompletedProcess(args=[], returncode=0),
            ) as run,
            patch("scripts.run_quality_gate.write_summary"),
            patch("scripts.run_quality_gate._register_history"),
            patch("scripts.run_quality_gate.print"),
        ):
            exit_code = run_quality_gate.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run.call_count, len(run_quality_gate.QUALITY_GATE_STEPS))

    def test_quality_gate_propaga_primeira_falha(self) -> None:
        results = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=7),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]

        with (
            patch(
                "scripts.run_quality_gate.subprocess.run",
                side_effect=results,
            ) as run,
            patch("scripts.run_quality_gate.write_summary"),
            patch("scripts.run_quality_gate._register_history"),
            patch("scripts.run_quality_gate.print"),
        ):
            exit_code = run_quality_gate.main()

        self.assertEqual(exit_code, 7)
        self.assertEqual(run.call_count, 2)

    def test_quality_gate_propaga_falha_da_auditoria(self) -> None:
        results = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=9),
        ]

        with (
            patch(
                "scripts.run_quality_gate.subprocess.run",
                side_effect=results,
            ) as run,
            patch("scripts.run_quality_gate.write_summary"),
            patch("scripts.run_quality_gate._register_history"),
            patch("scripts.run_quality_gate.print"),
        ):
            exit_code = run_quality_gate.main()

        self.assertEqual(exit_code, 9)
        self.assertEqual(run.call_count, 4)

    def test_quality_gate_emite_logs_minimos(self) -> None:
        with (
            patch(
                "scripts.run_quality_gate.subprocess.run",
                return_value=subprocess.CompletedProcess(args=[], returncode=0),
            ),
            patch("scripts.run_quality_gate.write_summary"),
            patch("scripts.run_quality_gate._register_history"),
            patch("scripts.run_quality_gate.print") as print_mock,
        ):
            exit_code = run_quality_gate.main()

        printed = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)

        self.assertEqual(exit_code, 0)
        self.assertIn("Iniciando validacao local", printed)
        self.assertIn("Analise estatica", printed)
        self.assertIn("Execucao principal", printed)
        self.assertIn("Testes automatizados", printed)
        self.assertIn("Auditoria arquitetural", printed)
        self.assertIn("Todas as etapas passaram", printed)


if __name__ == "__main__":
    unittest.main()
