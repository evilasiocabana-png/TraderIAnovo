"""Testes do relatorio oficial da Knowledge Base."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_index import KnowledgeIndex
from research.knowledge.knowledge_report import KnowledgeReport
from research.knowledge.knowledge_repository import KnowledgeRepository
from tests.architecture_test_utils import calls_from, imports_from, read_source


class KnowledgeReportTest(unittest.TestCase):
    """Valida consolidacao pura da Knowledge Base."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(KnowledgeReport))
        self.assertTrue(KnowledgeReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(KnowledgeReport)],
            [
                "artifacts",
                "repository",
                "index",
                "total_artifacts",
                "indexed_artifacts",
                "categories",
                "coverage",
                "quality_score",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.artifacts[0], KnowledgeArtifact)
        self.assertIsInstance(report.repository, KnowledgeRepository)
        self.assertIsInstance(report.index, KnowledgeIndex)

    def test_report_apresenta_campos_consolidados(self) -> None:
        report = self._report()

        self.assertEqual(report.total_artifacts, 2)
        self.assertEqual(report.indexed_artifacts, 2)
        self.assertEqual(report.categories, ("alpha", "campaign", "regime"))
        self.assertEqual(report.coverage, 1.0)
        self.assertEqual(report.quality_score, 0.85)
        self.assertEqual(report.execution_time, 4.2)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        artifacts = (self._artifact("artifact-001"),)
        repository = KnowledgeRepository()
        index = KnowledgeIndex()
        metadata = {"source": "unit-test"}

        report = KnowledgeReport(
            artifacts=artifacts,
            repository=repository,
            index=index,
            total_artifacts=1,
            indexed_artifacts=1,
            categories=("alpha",),
            coverage=1.0,
            quality_score=0.9,
            execution_time=1.5,
            metadata=metadata,
        )

        self.assertIs(report.artifacts, artifacts)
        self.assertIs(report.repository, repository)
        self.assertIs(report.index, index)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.quality_score = 0.0

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_report.py"))
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            " / ",
            " * ",
            " + ",
            " - ",
            ".index(",
            ".search(",
            ".filter(",
            ".list(",
            ".save(",
            ".run(",
            ".calculate(",
            ".validate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_report.py"))
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
            "persist",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/knowledge/knowledge_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> KnowledgeReport:
        artifacts = (
            self._artifact("artifact-001"),
            self._artifact("artifact-002"),
        )
        return KnowledgeReport(
            artifacts=artifacts,
            repository=KnowledgeRepository(),
            index=KnowledgeIndex(),
            total_artifacts=2,
            indexed_artifacts=2,
            categories=("alpha", "campaign", "regime"),
            coverage=1.0,
            quality_score=0.85,
            execution_time=4.2,
            metadata={"source": "unit-test"},
        )

    def _artifact(self, artifact_id: str) -> KnowledgeArtifact:
        return KnowledgeArtifact(
            artifact_id=artifact_id,
            alpha_id="Alpha003",
            research_id="research-alpha003-001",
            campaign_id="campaign-alpha003-001",
            hypothesis="Hipotese",
            conclusion="Conclusao",
            evidence=("Evidencia",),
            confidence=0.72,
            created_at=datetime(2026, 6, 28, 15, 0, 0),
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
