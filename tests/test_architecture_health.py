"""Testes do relatorio de saude arquitetural."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import architecture_health


class ArchitectureHealthTest(unittest.TestCase):
    """Valida indicadores consolidados de saude arquitetural."""

    def test_relatorio_e_gerado_em_markdown(self) -> None:
        report = architecture_health.build_health_report()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_health.md"
            architecture_health.write_report(report, path)
            markdown = path.read_text(encoding="utf-8")

        self.assertIn("# Architecture Health Report", markdown)
        self.assertIn("## Estrutura", markdown)
        self.assertIn("## Governanca", markdown)
        self.assertIn("Status geral", markdown)

    def test_formato_do_relatorio_e_consistente(self) -> None:
        report = architecture_health.build_health_report()

        expected_sections = {
            "status",
            "structure",
            "services",
            "domain",
            "dashboard",
            "replay",
            "research_lab",
            "providers",
            "event_bus",
            "tests",
            "governance",
        }

        self.assertTrue(expected_sections.issubset(report))
        self.assertIn("found_layers", report["structure"])
        self.assertIn("total_application_services", report["services"])
        self.assertIn("contracts_found", report["domain"])
        self.assertIn("events_count", report["event_bus"])

    def test_classificacao_e_calculada(self) -> None:
        report = architecture_health.build_health_report()

        self.assertIn(
            report["status"],
            {"EXCELENTE", "BOM", "ATENCAO", "CRITICO"},
        )

    def test_geracao_nao_altera_arquivos_protegidos(self) -> None:
        protected_paths = [
            architecture_health.ROOT / "architecture_manifest.json",
            architecture_health.ROOT / "architecture_baseline.json",
            architecture_health.ROOT / "README.md",
        ]
        before = {path: self._sha256(path) for path in protected_paths}

        report = architecture_health.build_health_report()
        markdown = architecture_health.to_markdown(report)

        after = {path: self._sha256(path) for path in protected_paths}

        self.assertIn("Architecture Health Report", markdown)
        self.assertEqual(before, after)

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
