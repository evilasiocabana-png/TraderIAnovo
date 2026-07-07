"""Relatorio oficial da validacao Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.validation.monte_carlo.monte_carlo_analyzer import (
    MonteCarloAnalysisResult,
)
from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult


@dataclass(frozen=True)
class MonteCarloReport:
    """Consolida resultados Monte Carlo sem realizar calculos."""

    monte_carlo_result: MonteCarloResult
    analysis_result: MonteCarloAnalysisResult
    simulations: int
    confidence_level: float
    average_return: float
    worst_case_return: float
    best_case_return: float
    expected_drawdown: float
    robustness_score: float
    execution_time: float
    metadata: Mapping[str, object]
