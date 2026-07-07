"""Testes do validador de consistencia de governanca."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import governance_consistency


class GovernanceConsistencyTest(unittest.TestCase):
    """Valida relatorio e deteccao de inconsistencias."""

    def test_script_gera_relatorio_json_valido(self) -> None:
        report = governance_consistency.build_report()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance_consistency.json"
            governance_consistency.write_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("status", loaded)
        self.assertIn("components_analyzed", loaded)
        self.assertIn(
            loaded["status"],
            {"CONSISTENT", "MINOR INCONSISTENCIES", "INCONSISTENT"},
        )

    def test_inconsistencias_sao_detectadas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_governance(root)
            baseline = json.loads((root / "architecture_baseline.json").read_text())
            baseline["services"] = []
            (root / "architecture_baseline.json").write_text(json.dumps(baseline), encoding="utf-8")

            report = governance_consistency.build_report(root)

        self.assertEqual(report["status"], "INCONSISTENT")
        self.assertTrue(report["inconsistencies"])

    def test_ausencia_de_arquivos_e_reportada(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_governance(root)
            (root / "scripts" / "run_quality_gate.py").unlink()

            report = governance_consistency.build_report(root)

        self.assertEqual(report["components_analyzed"]["scripts"]["scripts/run_quality_gate.py"], "MISSING")
        self.assertTrue(
            any(
                item["reference"] == "scripts/run_quality_gate.py"
                for item in report["inconsistencies"]
            )
        )

    def test_adrs_com_numeracao_quebrada_sao_reportados(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_governance(root)
            adr = root / "docs" / "adr"
            (adr / "ADR-0003-decisao.md").write_text(
                "# ADR\n\n- Status: Aprovado\n",
                encoding="utf-8",
            )
            (adr / "ADR-0002-decisao.md").unlink()

            report = governance_consistency.build_report(root)

        self.assertEqual(report["status"], "INCONSISTENT")
        self.assertTrue(
            any("Numeracao de ADR" in item["message"] for item in report["inconsistencies"])
        )

    def test_referencias_documentais_inexistentes_sao_reportadas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._minimal_governance(root)
            (root / "README.md").write_text("Ver docs/NAO_EXISTE.md\n", encoding="utf-8")

            report = governance_consistency.build_report(root)

        self.assertTrue(
            any(
                item["reference"] == "docs/NAO_EXISTE.md"
                for item in report["missing_references"]
            )
        )

    def _minimal_governance(self, root: Path) -> None:
        (root / "reports").mkdir(parents=True)
        (root / "docs" / "adr").mkdir(parents=True)
        (root / "scripts").mkdir()
        (root / "tests").mkdir()

        manifest = {
            "layers": ["application", "tests"],
            "public_services": ["DashboardService"],
            "domain_contracts": ["StrategySignal"],
            "providers": ["MarketDataProvider"],
            "adapters": ["CsvHistoricalDataSource"],
            "events": ["SYSTEM_STARTED"],
            "architecture_rules": ["domain_purity"],
            "architecture_rule_descriptions": {"domain_purity": "Domain puro."},
        }
        baseline = {
            "services": ["DashboardService"],
            "contracts": ["StrategySignal"],
            "providers": ["MarketDataProvider"],
            "adapters": ["CsvHistoricalDataSource"],
            "events": ["SYSTEM_STARTED"],
            "statistics": {
                "services": 1,
                "contracts": 1,
                "providers": 1,
                "adapters": 1,
            },
            "structure": {"layers": ["application", "tests"]},
        }
        audit = {"manifest_compliance": {"status": "OK"}}
        metrics = {"application": {"services": 1}}

        (root / "architecture_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "architecture_baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        (root / "reports" / "architecture_audit.json").write_text(json.dumps(audit), encoding="utf-8")
        (root / "reports" / "architecture_metrics.json").write_text(json.dumps(metrics), encoding="utf-8")

        docs = [
            "README.md",
            "TRADERIA_ARCHITECTURE_BIBLE.md",
            "ARCHITECTURE_RULES.md",
            "docs/ARCHITECTURE_INDEX.md",
            "docs/ARCHITECTURE_CHANGE_WORKFLOW.md",
            "docs/CI_PIPELINE.md",
            "docs/CI_FAILURE_TRIAGE.md",
        ]
        for relative in docs:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Governance document\n", encoding="utf-8")

        for number in (1, 2):
            (root / "docs" / "adr" / f"ADR-{number:04d}-decisao.md").write_text(
                "# ADR\n\n- Status: Aprovado\n\n## Referencias\n\n- README.md\n",
                encoding="utf-8",
            )

        for relative in governance_consistency.REQUIRED_SCRIPTS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# script\n", encoding="utf-8")

        for relative in governance_consistency.REQUIRED_GOVERNANCE_TESTS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# test\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
