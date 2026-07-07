"""Testes do contrato oficial de artefato de conhecimento."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest
from typing import Mapping, get_type_hints

from research.knowledge.knowledge_artifact import KnowledgeArtifact
from tests.architecture_test_utils import calls_from, imports_from, read_source


class KnowledgeArtifactTest(unittest.TestCase):
    """Valida DTO imutavel de conhecimento extraido da pesquisa."""

    def test_artifact_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(KnowledgeArtifact))
        self.assertTrue(KnowledgeArtifact.__dataclass_params__.frozen)

    def test_artifact_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(KnowledgeArtifact)],
            [
                "artifact_id",
                "alpha_id",
                "research_id",
                "campaign_id",
                "hypothesis",
                "conclusion",
                "evidence",
                "confidence",
                "created_at",
                "metadata",
            ],
        )

    def test_artifact_possui_type_hints_completos(self) -> None:
        hints = get_type_hints(KnowledgeArtifact)

        self.assertEqual(hints["artifact_id"], str)
        self.assertEqual(hints["alpha_id"], str)
        self.assertEqual(hints["research_id"], str)
        self.assertEqual(hints["campaign_id"], str)
        self.assertEqual(hints["hypothesis"], str)
        self.assertEqual(hints["conclusion"], str)
        self.assertEqual(hints["evidence"], tuple[str, ...])
        self.assertEqual(hints["confidence"], float)
        self.assertEqual(hints["created_at"], datetime)
        self.assertEqual(hints["metadata"], Mapping[str, object])

    def test_artifact_armazena_conhecimento_extraido_da_pesquisa(self) -> None:
        created_at = datetime(2026, 6, 28, 12, 0, 0)
        artifact = KnowledgeArtifact(
            artifact_id="knowledge-alpha003-001",
            alpha_id="Alpha003",
            research_id="research-alpha003-001",
            campaign_id="campaign-alpha003-001",
            hypothesis="Alpha003 captura rompimento intradiario controlado.",
            conclusion="Resultado promissor para pesquisa adicional.",
            evidence=("PF acima do limite.", "Drawdown controlado."),
            confidence=0.72,
            created_at=created_at,
            metadata={"source": "unit-test"},
        )

        self.assertEqual(artifact.artifact_id, "knowledge-alpha003-001")
        self.assertEqual(artifact.alpha_id, "Alpha003")
        self.assertEqual(artifact.research_id, "research-alpha003-001")
        self.assertEqual(artifact.campaign_id, "campaign-alpha003-001")
        self.assertIn("rompimento", artifact.hypothesis)
        self.assertEqual(artifact.conclusion, "Resultado promissor para pesquisa adicional.")
        self.assertEqual(artifact.evidence, ("PF acima do limite.", "Drawdown controlado."))
        self.assertEqual(artifact.confidence, 0.72)
        self.assertEqual(artifact.created_at, created_at)
        self.assertEqual(artifact.metadata["source"], "unit-test")

    def test_artifact_e_imutavel(self) -> None:
        artifact = self._artifact()

        with self.assertRaises(FrozenInstanceError):
            artifact.confidence = 0.0

    def test_nao_executa_pesquisa_ou_usa_ia(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_artifact.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".validate(",
            ".recommend(",
            "ResearchPipeline",
            "ResearchRunner",
            "openai",
            "llm",
            "chatgpt",
            "machine_learning",
            "sklearn",
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

    def test_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/knowledge/knowledge_artifact.py")
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
            "openai",
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

    def _artifact(self) -> KnowledgeArtifact:
        return KnowledgeArtifact(
            artifact_id="knowledge-alpha003-001",
            alpha_id="Alpha003",
            research_id="research-alpha003-001",
            campaign_id="campaign-alpha003-001",
            hypothesis="Hipotese validada em pesquisa.",
            conclusion="Conclusao consolidada.",
            evidence=("Evidencia 1.",),
            confidence=0.72,
            created_at=datetime(2026, 6, 28, 12, 0, 0),
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
