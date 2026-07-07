"""Contrato oficial de artefato de conhecimento."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class KnowledgeArtifact:
    """Representa conhecimento extraido da pesquisa sem executar rotinas."""

    artifact_id: str
    alpha_id: str
    research_id: str
    campaign_id: str
    hypothesis: str
    conclusion: str
    evidence: tuple[str, ...]
    confidence: float
    created_at: datetime
    metadata: Mapping[str, object]
