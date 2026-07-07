"""Relatorio oficial da validacao sob estresse."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.validation.stress.stress_analyzer import StressAnalysisResult
from research.validation.stress.stress_engine import StressResult
from research.validation.stress.stress_scenario import StressScenario


@dataclass(frozen=True)
class StressReport:
    """Consolida resultados sob estresse sem realizar calculos."""

    stress_result: StressResult
    analysis_result: StressAnalysisResult
    scenario: StressScenario
    degradation_score: float
    recovery_score: float
    resilience_score: float
    stability_score: float
    execution_time: float
    metadata: Mapping[str, object]
