"""Contratos da validacao de build reproduzivel."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import reproducible_build


class ReproducibleBuildTest(unittest.TestCase):
    """Valida comparacao deterministica sem executar comandos reais."""

    def _command(self, name: str, exit_code: int = 0) -> reproducible_build.CommandRun:
        return reproducible_build.CommandRun(
            name=name,
            command=f"python {name}",
            exit_code=exit_code,
            duration_seconds=0.1,
            stdout="ok",
            stderr="",
        )

    def test_diferencas_esperadas_sao_ignoradas(self) -> None:
        first = {
            "generated_at": "2026-06-27T10:00:00-03:00",
            "metrics": {"modules": 10, "duration_seconds": 1.0},
        }
        second = {
            "generated_at": "2026-06-27T10:01:00-03:00",
            "metrics": {"modules": 10, "duration_seconds": 2.0},
        }

        self.assertEqual(
            reproducible_build.normalize_json(first),
            reproducible_build.normalize_json(second),
        )

    def test_diferencas_estruturais_sao_detectadas(self) -> None:
        differences, _ = reproducible_build.compare_artifacts(
            {"architecture_metrics_json": {"modules": 10}},
            {"architecture_metrics_json": {"modules": 11}},
        )

        self.assertEqual(len(differences), 1)
        self.assertEqual(
            differences[0]["artifact"],
            "architecture_metrics_json",
        )

    def test_classificacao_non_reproducible_quando_ha_diferenca(self) -> None:
        classification = reproducible_build.classify(
            command_failures=[],
            differences=[{"artifact": "x"}],
            ignored_differences=[],
        )

        self.assertEqual(classification, "NON-REPRODUCIBLE")

    def test_relatorio_eh_gerado_com_json_valido(self) -> None:
        first = reproducible_build.BuildRun(
            index=1,
            commands=[self._command("app")],
            artifacts={"app_stdout": "ok"},
        )
        second = reproducible_build.BuildRun(
            index=2,
            commands=[self._command("app")],
            artifacts={"app_stdout": "ok"},
        )
        report = reproducible_build.build_report(first, second)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reproducible_build.json"
            reproducible_build.write_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("classification", loaded)
        self.assertIn("artifacts_compared", loaded)
        self.assertEqual(loaded["differences"], [])

    def test_comando_com_falha_torna_build_nao_reproduzivel(self) -> None:
        first = reproducible_build.BuildRun(
            index=1,
            commands=[self._command("app", exit_code=1)],
            artifacts={"app_stdout": "ok"},
        )
        second = reproducible_build.BuildRun(
            index=2,
            commands=[self._command("app")],
            artifacts={"app_stdout": "ok"},
        )

        report = reproducible_build.build_report(first, second)

        self.assertEqual(report["classification"], "NON-REPRODUCIBLE")
        self.assertEqual(report["command_failures"][0]["name"], "app")


if __name__ == "__main__":
    unittest.main()
