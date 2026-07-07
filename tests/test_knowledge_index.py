"""Testes do indice oficial da Knowledge Base."""

from datetime import datetime
from pathlib import Path
import unittest

from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_index import KnowledgeIndex
from tests.architecture_test_utils import calls_from, imports_from, read_source


class KnowledgeIndexTest(unittest.TestCase):
    """Valida organizacao em memoria dos artefatos de conhecimento."""

    def test_index_retorna_artefatos_indexados(self) -> None:
        artifacts = (self._artifact("artifact-001"), self._artifact("artifact-002"))
        index = KnowledgeIndex()

        indexed = index.index(artifacts)

        self.assertEqual(indexed, artifacts)

    def test_list_categories_retorna_categorias_oficiais(self) -> None:
        index = KnowledgeIndex()
        index.index((self._artifact("artifact-001"),))

        self.assertEqual(
            index.list_categories(),
            (
                "alpha",
                "campaign",
                "hypothesis",
                "feature",
                "context",
                "regime",
                "date",
            ),
        )

    def test_filter_organiza_por_alpha_campanha_hipotese_e_data(self) -> None:
        artifact = self._artifact(
            "artifact-001",
            alpha_id="Alpha003",
            campaign_id="campaign-alpha003-001",
            hypothesis="Parametros estaveis",
            created_at=datetime(2026, 6, 28, 14, 0, 0),
        )
        index = KnowledgeIndex()
        index.index((artifact,))

        self.assertEqual(index.filter("alpha", "alpha003"), (artifact,))
        self.assertEqual(
            index.filter("campaign", "campaign-alpha003-001"),
            (artifact,),
        )
        self.assertEqual(
            index.filter("hypothesis", "parametros estaveis"),
            (artifact,),
        )
        self.assertEqual(index.filter("date", "2026-06-28"), (artifact,))

    def test_filter_organiza_por_feature_contexto_e_regime(self) -> None:
        artifact = self._artifact(
            "artifact-001",
            metadata={
                "features": ("VWAP", "OpeningRange"),
                "contexts": ("abertura com volume",),
                "regimes": ("TREND", "VOLATILE"),
            },
        )
        index = KnowledgeIndex()
        index.index((artifact,))

        self.assertEqual(index.filter("feature", "vwap"), (artifact,))
        self.assertEqual(index.filter("feature", "openingrange"), (artifact,))
        self.assertEqual(
            index.filter("context", "abertura com volume"),
            (artifact,),
        )
        self.assertEqual(index.filter("regime", "trend"), (artifact,))
        self.assertEqual(index.filter("regime", "volatile"), (artifact,))

    def test_search_busca_em_campos_e_metadata(self) -> None:
        stable = self._artifact(
            "artifact-stable",
            hypothesis="Parametros estaveis",
            evidence=("stop=50",),
            metadata={"feature": "OpeningRange"},
        )
        regime = self._artifact(
            "artifact-regime",
            hypothesis="Regimes predominantes",
            evidence=("TREND",),
            metadata={"context": "abertura com volume"},
        )
        index = KnowledgeIndex()
        index.index((stable, regime))

        self.assertEqual(index.search("STOP=50"), (stable,))
        self.assertEqual(index.search("abertura"), (regime,))
        self.assertEqual(index.search(""), (stable, regime))

    def test_filter_categoria_ou_valor_inexistente_retorna_vazio(self) -> None:
        index = KnowledgeIndex()
        index.index((self._artifact("artifact-001"),))

        self.assertEqual(index.filter("feature", "atr"), ())
        self.assertEqual(index.filter("unknown", "alpha003"), ())

    def test_reindex_substitui_estado_anterior(self) -> None:
        first = self._artifact("artifact-001", alpha_id="Alpha001")
        second = self._artifact("artifact-002", alpha_id="Alpha002")
        index = KnowledgeIndex()

        index.index((first,))
        index.index((second,))

        self.assertEqual(index.filter("alpha", "alpha001"), ())
        self.assertEqual(index.filter("alpha", "alpha002"), (second,))

    def test_index_nao_executa_pesquisa_ou_recalcula_conhecimento(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_index.py"))
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "KnowledgeRepository",
            "ResearchReport",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".generate(",
            ".calculate(",
            ".validate(",
            "open(",
            "write(",
            "read_text",
            "write_text",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_index_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/knowledge/knowledge_index.py")
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
            "research.knowledge.knowledge_repository",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "generate",
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
        alpha_id: str = "Alpha003",
        campaign_id: str = "campaign-alpha003-001",
        hypothesis: str = "Hipotese",
        conclusion: str = "Conclusao",
        evidence: tuple[str, ...] = ("Evidencia",),
        created_at: datetime = datetime(2026, 6, 28, 14, 0, 0),
        metadata: dict[str, object] | None = None,
    ) -> KnowledgeArtifact:
        return KnowledgeArtifact(
            artifact_id=artifact_id,
            alpha_id=alpha_id,
            research_id="research-alpha003-001",
            campaign_id=campaign_id,
            hypothesis=hypothesis,
            conclusion=conclusion,
            evidence=evidence,
            confidence=0.72,
            created_at=created_at,
            metadata=metadata or {},
        )


if __name__ == "__main__":
    unittest.main()
