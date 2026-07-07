"""Relatorio oficial da Knowledge Base."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_index import KnowledgeIndex
from research.knowledge.knowledge_repository import KnowledgeRepository


@dataclass(frozen=True)
class KnowledgeReport:
    """Consolida informacoes da Knowledge Base sem realizar calculos."""

    artifacts: tuple[KnowledgeArtifact, ...]
    repository: KnowledgeRepository
    index: KnowledgeIndex
    total_artifacts: int
    indexed_artifacts: int
    categories: tuple[str, ...]
    coverage: float
    quality_score: float
    execution_time: float
    metadata: Mapping[str, object]
