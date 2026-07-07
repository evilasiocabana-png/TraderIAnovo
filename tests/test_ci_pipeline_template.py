"""Valida o template inicial de CI do TraderIA_WDO."""

from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/quality-gate.yml")


class CiPipelineTemplateTest(unittest.TestCase):
    """Contratos de seguranca e validacao do workflow de CI."""

    def setUp(self) -> None:
        self.source = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.normalized = self.source.lower()

    def test_quality_gate_workflow_existe(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists())

    def test_yaml_possui_jobs(self) -> None:
        self.assertIn("jobs:", self.source)
        self.assertIn("quality-gate:", self.source)
        self.assertIn("steps:", self.source)

    def test_pipeline_chama_validacoes_oficiais(self) -> None:
        required_commands = [
            "python scripts/run_static_analysis.py",
            "python scripts/run_quality_gate.py",
            "python scripts/architecture_audit.py",
            "python -m unittest discover -s tests",
        ]

        for command in required_commands:
            with self.subTest(command=command):
                self.assertIn(command, self.source)

    def test_pipeline_nao_chama_streamlit_bloqueante(self) -> None:
        self.assertNotIn("streamlit run", self.normalized)
        self.assertNotIn("python -m streamlit run", self.normalized)

    def test_pipeline_nao_altera_baseline_ou_manifesto(self) -> None:
        forbidden = [
            "create_architecture_baseline.py",
            "architecture_baseline.json >",
            "> architecture_baseline.json",
            "manifest.md >",
            "> manifest.md",
        ]

        for command in forbidden:
            with self.subTest(command=command):
                self.assertNotIn(command, self.normalized)

    def test_pipeline_nao_contem_comandos_de_operacao_real(self) -> None:
        forbidden_terms = [
            "metatrader5",
            "mt5",
            "corretora",
            "broker real",
            "send_order",
            "order_send",
            "enviar_ordem_real",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, self.normalized)

    def test_pipeline_configura_artefatos_permitidos(self) -> None:
        expected_artifacts = [
            "reports/quality_gate_summary.json",
            "reports/architecture_audit.md",
            "reports/architecture_audit.json",
            "reports/static_analysis_report.json",
            "reports/ci_readiness.json",
            "reports/reproducible_build.json",
            "reports/repository_compliance.json",
            "reports/failure_context.json",
            "reports/architecture_health.md",
            "reports/architecture_metrics.json",
        ]

        self.assertIn("actions/upload-artifact", self.source)
        for artifact in expected_artifacts:
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, self.source)

    def test_pipeline_configura_retencao_de_artefatos(self) -> None:
        self.assertIn("retention-days: 30", self.source)
        self.assertIn("retention-days: 90", self.source)
        self.assertIn("traderia-quality-reports", self.source)
        self.assertIn("traderia-architecture-audit-reports", self.source)

    def test_pipeline_nao_publica_artefatos_sensiveis_ou_datasets(self) -> None:
        forbidden_artifacts = [
            "data/",
            "data/**",
            "logs/",
            "logs/**",
            "architecture_baseline.json",
            "manifest.md",
            ".env",
            "*.key",
            "*.pem",
            "token",
            "secret",
            "credential",
            "credencial",
        ]

        for artifact in forbidden_artifacts:
            with self.subTest(artifact=artifact):
                self.assertNotIn(artifact, self.normalized)


if __name__ == "__main__":
    unittest.main()
