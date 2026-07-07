"""Validacoes estruturais da configuracao de CI."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/quality-gate.yml")


class CiConfigurationTest(unittest.TestCase):
    """Protege a politica oficial do workflow de CI."""

    def setUp(self) -> None:
        self.source = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.normalized = self.source.lower()

    def test_workflow_existe(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists())

    def test_jobs_obrigatorios_estao_presentes(self) -> None:
        expected_fragments = [
            "Checkout repository",
            "Setup Python",
            "Install dependencies",
            "Static analysis",
            "Quality Gate",
            "Architecture audit",
            "Tests",
        ]

        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)

    def test_ordem_logica_das_etapas_permanece(self) -> None:
        ordered_fragments = [
            "Checkout repository",
            "Setup Python",
            "Install dependencies",
            "Static analysis",
            "Quality Gate",
            "Architecture audit",
            "Tests",
        ]

        positions = [
            self.source.index(f"- name: {fragment}")
            for fragment in ordered_fragments
        ]

        self.assertEqual(positions, sorted(positions))

    def test_comandos_oficiais_estao_configurados(self) -> None:
        expected_commands = [
            "python scripts/run_static_analysis.py",
            "python scripts/run_quality_gate.py",
            "python scripts/architecture_audit.py",
            "python -m unittest discover -s tests",
        ]

        for command in expected_commands:
            with self.subTest(command=command):
                self.assertIn(command, self.source)

    def test_restricoes_operacionais_sao_preservadas(self) -> None:
        forbidden_terms = [
            "streamlit run",
            "python -m streamlit run",
            "broker",
            "mt5",
            "metatrader",
            "corretora",
            "envio de ordens",
            "execucao operacional",
            "execução operacional",
            "send_order",
            "order_send",
            "enviar_ordem",
            "create_architecture_baseline.py",
            "architecture_baseline.json >",
            "> architecture_baseline.json",
            "manifest.md >",
            "> manifest.md",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, self.normalized)

    def test_somente_relatorios_autorizados_sao_publicados(self) -> None:
        authorized_paths = {
            "reports/quality_gate_summary.json",
            "reports/static_analysis_report.json",
            "reports/ci_readiness.json",
            "reports/reproducible_build.json",
            "reports/repository_compliance.json",
            "reports/failure_context.json",
            "reports/architecture_audit.md",
            "reports/architecture_audit.json",
            "reports/architecture_health.md",
            "reports/architecture_metrics.json",
        }
        published_paths = set(re.findall(r"^\s+(reports/[^\s]+)$", self.source, re.MULTILINE))

        self.assertEqual(published_paths, authorized_paths)

    def test_artefatos_proibidos_nao_sao_publicados(self) -> None:
        forbidden_artifact_patterns = [
            "data/",
            "data/**",
            "logs/",
            "logs/**",
            ".env",
            "config.local",
            "credentials",
            "credenciais",
            "secrets",
            "tokens",
            "cache/",
            "architecture_baseline.json",
            "manifest.md",
        ]

        for pattern in forbidden_artifact_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, self.normalized)

    def test_seguranca_nao_expoe_credenciais(self) -> None:
        forbidden_security_patterns = [
            r"(?i)password\s*[:=]\s*['\"][^'\"]+",
            r"(?i)token\s*[:=]\s*['\"][^'\"]+",
            r"(?i)secret\s*[:=]\s*['\"][^'\"]+",
            r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+",
            r"https://[^/\s]*internal[^/\s]*",
            r"https://[^/\s]*private[^/\s]*",
        ]

        for pattern in forbidden_security_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
