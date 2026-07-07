"""Contratos do historico de execucoes do Quality Gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import quality_gate_history
from scripts import run_quality_gate


class QualityGateHistoryTest(unittest.TestCase):
    """Valida registro historico sem executar comandos reais."""

    def _summary(self, timestamp: str = "2026-06-27T10:00:00-03:00") -> dict[str, object]:
        return {
            "executed_at": timestamp,
            "overall_status": "PASSED",
            "total_duration_seconds": 12.3,
            "steps": {
                "static_analysis": {
                    "status": "PASSED",
                    "duration_seconds": 1.0,
                    "exit_code": 0,
                },
                "test_suite": {
                    "status": "PASSED",
                    "duration_seconds": 10.0,
                    "exit_code": 0,
                },
                "architecture_audit": {
                    "status": "PASSED",
                    "duration_seconds": 1.3,
                    "exit_code": 0,
                },
            },
        }

    def _diagnostics(self) -> dict[str, object]:
        return {
            "summary": {
                "total_tests": 1037,
                "failures": 0,
                "errors": 0,
            }
        }

    def test_historico_criado_automaticamente(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "summary.json"
            diagnostics_path = root / "diagnostics.json"
            history_path = root / "quality_gate_history.json"
            summary_path.write_text(json.dumps(self._summary()), encoding="utf-8")
            diagnostics_path.write_text(
                json.dumps(self._diagnostics()),
                encoding="utf-8",
            )

            with patch(
                "scripts.quality_gate_history.discovered_test_count",
                return_value=1037,
            ):
                history = quality_gate_history.register_quality_gate_execution(
                    summary_path=summary_path,
                    diagnostics_path=diagnostics_path,
                    history_path=history_path,
                    version="CTO-TEST",
                    commit="abc123",
                )
            loaded = json.loads(history_path.read_text(encoding="utf-8"))

        self.assertEqual(len(history["history"]), 1)
        self.assertEqual(loaded["history"][0]["project_version"], "CTO-TEST")
        self.assertEqual(loaded["history"][0]["commit"], "abc123")
        self.assertEqual(loaded["history"][0]["tests"]["total"], 1037)

    def test_novo_registro_adicionado_corretamente(self) -> None:
        first = quality_gate_history.build_history_record(
            self._summary("2026-06-27T10:00:00-03:00"),
            self._diagnostics(),
        )
        second = quality_gate_history.build_history_record(
            self._summary("2026-06-27T11:00:00-03:00"),
            self._diagnostics(),
        )

        history = quality_gate_history.append_history_record(
            {"history": [first]},
            second,
        )

        self.assertEqual(len(history["history"]), 2)
        self.assertEqual(history["history"][1]["timestamp"], second["timestamp"])

    def test_limite_maximo_de_registros_respeitado(self) -> None:
        history: dict[str, object] = {"history": []}
        for index in range(5):
            record = quality_gate_history.build_history_record(
                self._summary(f"2026-06-27T10:0{index}:00-03:00"),
                self._diagnostics(),
            )
            history = quality_gate_history.append_history_record(
                history,
                record,
                max_records=3,
            )

        self.assertEqual(len(history["history"]), 3)
        self.assertEqual(
            [entry["timestamp"] for entry in history["history"]],
            [
                "2026-06-27T10:02:00-03:00",
                "2026-06-27T10:03:00-03:00",
                "2026-06-27T10:04:00-03:00",
            ],
        )

    def test_registros_permanecem_ordenados(self) -> None:
        late = quality_gate_history.build_history_record(
            self._summary("2026-06-27T12:00:00-03:00"),
            self._diagnostics(),
        )
        early = quality_gate_history.build_history_record(
            self._summary("2026-06-27T09:00:00-03:00"),
            self._diagnostics(),
        )

        history = quality_gate_history.append_history_record(
            {"history": [late]},
            early,
        )

        self.assertEqual(
            [entry["timestamp"] for entry in history["history"]],
            [
                "2026-06-27T09:00:00-03:00",
                "2026-06-27T12:00:00-03:00",
            ],
        )

    def test_json_valido(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            history = quality_gate_history.append_history_record(
                {"history": []},
                quality_gate_history.build_history_record(
                    self._summary(),
                    self._diagnostics(),
                ),
            )
            quality_gate_history.write_history(history, path)

            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("history", loaded)
        self.assertEqual(loaded["history"][0]["status"], "PASSED")

    def test_quality_gate_integra_historico_sem_mudar_exit_code(self) -> None:
        results = [
            run_quality_gate.QualityGateStepResult(
                step=step,
                status="PASSED",
                duration_seconds=0.1,
                exit_code=0,
                message="ok",
            )
            for step in run_quality_gate.QUALITY_GATE_STEPS
        ]

        with (
            patch("scripts.run_quality_gate.write_summary"),
            patch("scripts.run_quality_gate._register_history") as register,
        ):
            run_quality_gate._write_summary_for_results(results)

        register.assert_called_once()


if __name__ == "__main__":
    unittest.main()
