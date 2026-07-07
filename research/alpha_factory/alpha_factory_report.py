"""Relatorio consolidado da Alpha Factory."""

from dataclasses import dataclass
from datetime import datetime

from research.alpha_factory.alpha_candidate_registry import AlphaCandidateRegistry
from research.alpha_factory.alpha_hypothesis import AlphaHypothesis
from research.alpha_factory.alpha_playbook_template import AlphaPlaybookTemplate
from research.alpha_factory.alpha_readiness_validator import AlphaReadinessResult


@dataclass(frozen=True)
class AlphaFactoryReport:
    """Agrega informacoes produzidas pela Alpha Factory."""

    hypothesis: AlphaHypothesis
    playbook: AlphaPlaybookTemplate
    readiness_result: AlphaReadinessResult
    candidate_registry: AlphaCandidateRegistry
    hypothesis_id: str
    alpha_name: str
    version: int
    readiness_status: str
    validation_messages: tuple[str, ...]
    candidate_status: str
    created_at: datetime
