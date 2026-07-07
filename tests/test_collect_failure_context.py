"""Testes do coletor de contexto de falhas."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import collect_failure_context


class CollectFailureContextTest(unittest.TestCase):
    """Valida geracao de diagnostico consolidado."""

    def test_script_gera_relatorio_json_valido(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "quality_gate_summary.json").write_text(
                json.dumps({"overall_status": "PASSED"}),
                encoding="utf-8",
            )
            report_path = reports / "failure_context.json"

            report = collect_failure_context.build_failure_context(root=root)
            collect_failure_context.write_report(report, report_path)
            loaded = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertEqual(loaded["reports_found"]["quality_gate_summary"]["status"], "PASSED")
            self.assertIn("reports/test_failure_diagnostics.json", loaded["reports_missing"])

    def test_relatorios_ausentes_nao_geram_excecao(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = collect_failure_context.build_failure_context(root=Path(tmp))

            self.assertEqual(report["overall_status"], "WARNING")
            self.assertGreater(len(report["reports_missing"]), 0)
            self.assertEqual(report["reports_found"], {})

    def test_falhas_sao_agrupadas_por_categoria(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "test_failure_diagnostics.json").write_text(
                json.dumps(
                    {
                        "status": "FAILED",
                        "failures_by_category": {
                            "replay": [
                                {
                                    "test": "test_replay_contract",
                                    "file": "tests/test_replay.py",
                                    "message": "Replay contract failed.",
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = collect_failure_context.build_failure_context(root=root)

            self.assertEqual(report["overall_status"], "FAILED")
            self.assertIn("unit_tests", report["failures_by_category"])
            self.assertIn("replay", report["failures_by_category"])

    def test_status_de_falha_de_relatorio_propaga_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "ci_readiness.json").write_text(
                json.dumps({"status": "NOT READY", "message": "Dependencia ausente."}),
                encoding="utf-8",
            )

            report = collect_failure_context.build_failure_context(root=root)

            self.assertEqual(report["overall_status"], "FAILED")
            self.assertIn("ci_readiness", report["failures_by_category"])

    def test_formato_atual_da_auditoria_arquitetural_e_reconhecido(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "architecture_audit.json").write_text(
                json.dumps(
                    {
                        "manifest_compliance": {"status": "OK"},
                        "architecture_baseline_drift": {
                            "status": "DRIFT",
                            "criticality": "INFORMATIVO",
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = collect_failure_context.build_failure_context(root=root)

            self.assertEqual(report["reports_found"]["architecture_audit"]["status"], "OK")

    def test_nao_modifica_fora_do_relatorio_de_saida(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            existing = reports / "quality_gate_summary.json"
            existing.write_text(json.dumps({"overall_status": "PASSED"}), encoding="utf-8")
            before = {
                path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
                for path in root.rglob("*")
                if path.is_file()
            }

            report = collect_failure_context.build_failure_context(root=root)
            collect_failure_context.write_report(report, reports / "failure_context.json")
            after = {
                path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
                for path in root.rglob("*")
                if path.is_file()
            }

            changed = {
                path
                for path, content in after.items()
                if before.get(path) != content
            }
            self.assertEqual(changed, {"reports/failure_context.json"})


if __name__ == "__main__":
    unittest.main()
