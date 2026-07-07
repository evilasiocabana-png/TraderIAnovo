"""Repositorio em memoria para conhecimento produzido pelo Research Lab."""

from __future__ import annotations

from dataclasses import dataclass, field

from research.knowledge.knowledge_artifact import KnowledgeArtifact


@dataclass
class KnowledgeRepository:
    """Gerencia artefatos de conhecimento em memoria."""

    _artifacts: dict[str, KnowledgeArtifact] = field(
        default_factory=dict,
        init=False,
    )

    def save(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact:
        """Salva ou substitui um artefato de conhecimento em memoria."""
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get(self, artifact_id: str) -> KnowledgeArtifact | None:
        """Retorna um artefato pelo identificador."""
        return self._artifacts.get(artifact_id)

    def list(self) -> tuple[KnowledgeArtifact, ...]:
        """Lista os artefatos armazenados em memoria."""
        return tuple(self._artifacts.values())

    def search(self, query: str) -> tuple[KnowledgeArtifact, ...]:
        """Busca artefatos por texto em campos estruturados."""
        normalized = query.casefold().strip()
        if not normalized:
            return self.list()
        return tuple(
            artifact
            for artifact in self._artifacts.values()
            if normalized in self._search_text(artifact)
        )

    def delete(self, artifact_id: str) -> bool:
        """Remove um artefato quando ele existir."""
        if artifact_id not in self._artifacts:
            return False
        del self._artifacts[artifact_id]
        return True

    def _search_text(self, artifact: KnowledgeArtifact) -> str:
        values = (
            artifact.artifact_id,
            artifact.alpha_id,
            artifact.research_id,
            artifact.campaign_id,
            artifact.hypothesis,
            artifact.conclusion,
            *artifact.evidence,
            *(str(key) for key in artifact.metadata.keys()),
            *(str(value) for value in artifact.metadata.values()),
        )
        return " ".join(values).casefold()
