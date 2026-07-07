"""Testes do repositorio oficial de conhecimento."""

from datetime import datetime
from pathlib import Path
import unittest

from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_repository import KnowledgeRepository
from tests.architecture_test_utils import calls_from, imports_from, read_source


class KnowledgeRepositoryTest(unittest.TestCase):
    """Valida armazenamento em memoria de artefatos de conhecimento."""

    def test_save_e_get_armazenam_artefato(self) -> None:
        repository = KnowledgeRepository()
        artifact = self._artifact("artifact-001", hypothesis="Hipotese A")

        saved = repository.save(artifact)

        self.assertIs(saved, artifact)
        self.assertIs(repository.get("artifact-001"), artifact)

    def test_save_substitui_artefato_com_mesmo_id(self) -> None:
        repository = KnowledgeRepository()
        original = self._artifact("artifact-001", conclusion="Original")
        updated = self._artifact("artifact-001", conclusion="Atualizado")

        repository.save(original)
        repository.save(updated)

        self.assertEqual(repository.list(), (updated,))
        self.assertEqual(repository.get("artifact-001").conclusion, "Atualizado")

    def test_list_retorna_artefatos_em_memoria(self) -> None:
        repository = KnowledgeRepository()
        first = self._artifact("artifact-001")
        second = self._artifact("artifact-002")

        repository.save(first)
        repository.save(second)

        self.assertEqual(repository.list(), (first, second))

    def test_search_busca_em_campos_e_evidencias(self) -> None:
        repository = KnowledgeRepository()
        stable = self._artifact(
            "artifact-stable",
            hypothesis="Parametros estaveis",
            evidence=("stop=50", "target=100"),
        )
        regime = self._artifact(
            "artifact-regime",
            hypothesis="Regimes predominantes",
            evidence=("TREND",),
        )
        repository.save(stable)
        repository.save(regime)

        self.assertEqual(repository.search("target=100"), (stable,))
        self.assertEqual(repository.search("trend"), (regime,))
        self.assertEqual(repository.search("PARAMETROS"), (stable,))

    def test_search_busca_em_metadata_e_retorna_todos_para_query_vazia(self) -> None:
        repository = KnowledgeRepository()
        artifact = self._artifact(
            "artifact-001",
            metadata={"category": "limitations", "source": "unit-test"},
        )
        repository.save(artifact)

        self.assertEqual(repository.search("limitations"), (artifact,))
        self.assertEqual(repository.search("   "), (artifact,))

    def test_delete_remove_quando_existe(self) -> None:
        repository = KnowledgeRepository()
        repository.save(self._artifact("artifact-001"))

        self.assertTrue(repository.delete("artifact-001"))
        self.assertIsNone(repository.get("artifact-001"))
        self.assertFalse(repository.delete("artifact-001"))

    def test_repositorios_sao_isolados_em_memoria(self) -> None:
        first_repository = KnowledgeRepository()
        second_repository = KnowledgeRepository()

        first_repository.save(self._artifact("artifact-001"))

        self.assertEqual(len(first_repository.list()), 1)
        self.assertEqual(second_repository.list(), ())

    def test_repository_nao_usa_persistencia_externa(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_repository.py"))
        forbidden_fragments = (
            "sqlite",
            "postgres",
            "redis",
            "open(",
            "write(",
            "read_text",
            "write_text",
            "json",
            "csv",
            "pickle",
            "Path(",
            "ResearchPipeline",
            "ResearchRunner",
            "ExperimentRepository",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_repository_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/knowledge/knowledge_repository.py")
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
            "research.experiment_repository",
            "sqlite3",
            "redis",
            "psycopg",
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
            "read_text",
            "write_text",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _artifact(
        self,
        artifact_id: str,
        hypothesis: str = "Hipotese",
        conclusion: str = "Conclusao",
        evidence: tuple[str, ...] = ("Evidencia",),
        metadata: dict[str, object] | None = None,
    ) -> KnowledgeArtifact:
        return KnowledgeArtifact(
            artifact_id=artifact_id,
            alpha_id="Alpha003",
            research_id="research-alpha003-001",
            campaign_id="campaign-alpha003-001",
            hypothesis=hypothesis,
            conclusion=conclusion,
            evidence=evidence,
            confidence=0.72,
            created_at=datetime(2026, 6, 28, 14, 0, 0),
            metadata=metadata or {},
        )


if __name__ == "__main__":
    unittest.main()
