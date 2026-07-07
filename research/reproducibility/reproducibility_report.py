"""Relatorio oficial de reprodutibilidade do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass

from research.reproducibility.experiment_fingerprint import ExperimentFingerprintResult
from research.reproducibility.reproducibility_validator import (
    ReproducibilityValidationResult,
)
from research.reproducibility.research_snapshot import ResearchSnapshot


@dataclass(frozen=True)
class ReproducibilityReport:
    """Consolida os resultados de reprodutibilidade de uma pesquisa."""

    snapshot: ResearchSnapshot
    fingerprint_result: ExperimentFingerprintResult
    validation_result: ReproducibilityValidationResult
    experiment_id: str
    fingerprint: str
    compatible_versions: bool
    configuration_status: str
    dataset_status: str
    replay_status: str
    reproducibility_score: float
    execution_time: float
