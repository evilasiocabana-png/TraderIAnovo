"""Testes do dashboard executivo de governanca."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import governance_dashboard


class GovernanceDashboardTest(unittest.TestCase):
    """Valida consolidacao executiva dos relatorios de governanca."""

    def test_script_gera_relatorio_consolidado_json_valido(self) -> None:
        report = governance_dashboard.build_dashboard()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance_dashboard.json"
            governance_dashboard.write_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("overall_classification", loaded)
        self.assertIn("reports_consolidated", loaded)
        self.assertIn("indicators", loaded)

    def test_ausencia_de_relatorio_individual_nao_quebra_execucao(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            self._write_json(
                root,
                "reports/quality_gate_summary.json",
                {"overall_status": "PASSED"},
            )

            report = governance_dashboard.build_dashboard(root)

        self.assertEqual(
            report["reports_consolidated"]["architecture_audit"]["status"],
            "MISSING",
        )
        self.assertIn(
            report["overall_classification"],
            {"EXCELLENT", "GOOD", "ATTENTION", "CRITICAL"},
        )

    def test_classificacao_critical_para_relatorio_obrigatorio_ausente(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()

            report = governance_dashboard.build_dashboard(root)

        self.assertEqual(report["overall_classification"], "CRITICAL")

    def test_classificacao_attention_para_governanca_inconsistente(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_reports(root, governance_status="INCONSISTENT")

            report = governance_dashboard.build_dashboard(root)

        self.assertEqual(report["overall_classification"], "ATTENTION")

    def test_classificacao_good_para_avisos_sem_inconsistencia(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_reports(root, governance_status="CONSISTENT")
            self._write_json(
                root,
                "reports/reproducible_build.json",
                {"status": "REPRODUCIBLE WITH WARNINGS"},
            )

            report = governance_dashboard.build_dashboard(root)

        self.assertEqual(report["overall_classification"], "GOOD")

    def _minimal_reports(self, root: Path, *, governance_status: str) -> None:
        (root / "reports").mkdir(parents=True, exist_ok=True)
        self._write_json(root, "reports/quality_gate_summary.json", {"overall_status": "PASSED"})
        self._write_json(
            root,
            "reports/architecture_audit.json",
            {"manifest_compliance": {"status": "OK"}},
        )
        self._write_json(
            root,
            "reports/architecture_metrics.json",
            {
                "architecture": {"architectural_violations_count": 0},
                "testing": {"architectural_tests_percentage": 10.0},
            },
        )
        self._write_json(
            root,
            "reports/governance_consistency.json",
            {
                "status": governance_status,
                "components_analyzed": {
                    "adrs": {
                        "files": [
                            "ADR-0008-ia-nao-executa-ordens.md",
                            "ADR-0009-operacao-real-desabilitada.md",
                        ]
                    },
                    "documentation": {"workflow": {"exists": True}},
                },
                "documentation_divergences": [],
                "missing_references": [],
            },
        )
        self._write_json(root, "reports/ci_readiness.json", {"status": "READY"})
        self._write_json(root, "reports/reproducible_build.json", {"status": "REPRODUCIBLE"})
        self._write_json(root, "reports/static_analysis_report.json", {"status": "OK"})
        self._write_json(root, "reports/test_performance_budget.json", {"status": "PASSED"})
        self._write_json(root, "reports/test_failure_diagnostics.json", {"status": "PASSED"})
        self._write_json(root, "reports/failure_context.json", {"overall_status": "PASSED"})
        (root / "reports" / "architecture_health.md").write_text(
            "\n".join(
                [
                    "# Architecture Health Report",
                    "- Status geral: BOM",
                    "- Baseline drift: NONE",
                    "- Criticidade do drift: nenhuma",
                    "- Replay protegido: OK",
                    "- Sem acesso a infraestrutura operacional: OK",
                    "- Research protegido: OK",
                ]
            ),
            encoding="utf-8",
        )

    def _write_json(self, root: Path, relative: str, data: dict[str, object]) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
