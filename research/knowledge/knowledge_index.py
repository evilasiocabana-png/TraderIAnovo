"""Indice em memoria da Knowledge Base."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from research.knowledge.knowledge_artifact import KnowledgeArtifact


@dataclass
class KnowledgeIndex:
    """Organiza artefatos de conhecimento por categorias oficiais."""

    _artifacts: tuple[KnowledgeArtifact, ...] = field(
        default_factory=tuple,
        init=False,
    )
    _categories: dict[str, dict[str, tuple[KnowledgeArtifact, ...]]] = field(
        default_factory=dict,
        init=False,
    )

    def index(
        self,
        artifacts: Iterable[KnowledgeArtifact],
    ) -> tuple[KnowledgeArtifact, ...]:
        """Indexa artefatos recebidos sem recalcular conhecimento."""
        self._artifacts = tuple(artifacts)
        self._categories = self._build_categories(self._artifacts)
        return self._artifacts

    def search(self, query: str) -> tuple[KnowledgeArtifact, ...]:
        """Busca artefatos por texto nos campos indexados."""
        normalized = query.casefold().strip()
        if not normalized:
            return self._artifacts
        return tuple(
            artifact
            for artifact in self._artifacts
            if normalized in self._search_text(artifact)
        )

    def filter(
        self,
        category: str,
        value: str,
    ) -> tuple[KnowledgeArtifact, ...]:
        """Filtra artefatos por categoria e valor indexados."""
        category_key = category.casefold().strip()
        value_key = value.casefold().strip()
        return self._categories.get(category_key, {}).get(value_key, ())

    def list_categories(self) -> tuple[str, ...]:
        """Lista categorias disponiveis no indice."""
        return tuple(self._categories.keys())

    def _build_categories(
        self,
        artifacts: tuple[KnowledgeArtifact, ...],
    ) -> dict[str, dict[str, tuple[KnowledgeArtifact, ...]]]:
        categories: dict[str, dict[str, list[KnowledgeArtifact]]] = {
            "alpha": {},
            "campaign": {},
            "hypothesis": {},
            "feature": {},
            "context": {},
            "regime": {},
            "date": {},
        }
        for artifact in artifacts:
            self._add(categories, "alpha", artifact.alpha_id, artifact)
            self._add(categories, "campaign", artifact.campaign_id, artifact)
            self._add(categories, "hypothesis", artifact.hypothesis, artifact)
            self._add(categories, "date", self._date_key(artifact.created_at.date()), artifact)
            for value in self._metadata_values(artifact, ("feature", "features")):
                self._add(categories, "feature", value, artifact)
            for value in self._metadata_values(artifact, ("context", "contexts")):
                self._add(categories, "context", value, artifact)
            for value in self._metadata_values(artifact, ("regime", "regimes")):
                self._add(categories, "regime", value, artifact)
        return {
            category: {
                value: tuple(items)
                for value, items in values.items()
            }
            for category, values in categories.items()
        }

    def _add(
        self,
        categories: dict[str, dict[str, list[KnowledgeArtifact]]],
        category: str,
        value: object,
        artifact: KnowledgeArtifact,
    ) -> None:
        key = str(value).casefold().strip()
        if not key:
            return
        categories[category].setdefault(key, []).append(artifact)

    def _metadata_values(
        self,
        artifact: KnowledgeArtifact,
        keys: tuple[str, ...],
    ) -> tuple[str, ...]:
        values: list[str] = []
        for key in keys:
            raw_value = artifact.metadata.get(key)
            if raw_value is None:
                continue
            if isinstance(raw_value, str):
                values.append(raw_value)
                continue
            if isinstance(raw_value, Iterable):
                values.extend(str(item) for item in raw_value)
                continue
            values.append(str(raw_value))
        return tuple(values)

    def _search_text(self, artifact: KnowledgeArtifact) -> str:
        values = (
            artifact.artifact_id,
            artifact.alpha_id,
            artifact.research_id,
            artifact.campaign_id,
            artifact.hypothesis,
            artifact.conclusion,
            self._date_key(artifact.created_at.date()),
            *artifact.evidence,
            *(str(key) for key in artifact.metadata.keys()),
            *(str(value) for value in artifact.metadata.values()),
        )
        return " ".join(values).casefold()

    def _date_key(self, value: date) -> str:
        return value.isoformat()
