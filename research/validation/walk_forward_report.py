"""Relatorio oficial da validacao Walk-Forward."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.validation.walk_forward_analyzer import WalkForwardAnalysisResult
from research.validation.walk_forward_engine import WalkForwardResult


@dataclass(frozen=True)
class WalkForwardReport:
    """Consolida resultados Walk-Forward sem realizar calculos."""

    walk_forward_result: WalkForwardResult
    analysis_result: WalkForwardAnalysisResult
    training_summary: str
    validation_summary: str
    testing_summary: str
    degradation_score: float
    stability_score: float
    consistency_score: float
    execution_time: float
    metadata: Mapping[str, object]
