"""Relatorio oficial da evolucao do portfolio quantitativo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.portfolio.portfolio_admission_engine import PortfolioAdmissionResult
from research.portfolio.portfolio_candidate import PortfolioCandidate
from research.portfolio.portfolio_replacement_engine import (
    PortfolioReplacementResult,
)


@dataclass(frozen=True)
class PortfolioEvolutionReport:
    """Consolida resultados de evolucao do portfolio sem calcular."""

    candidates: tuple[PortfolioCandidate, ...]
    admission_results: tuple[PortfolioAdmissionResult, ...]
    replacement_results: tuple[PortfolioReplacementResult, ...]
    total_candidates: int
    admitted: int
    rejected: int
    replaced: int
    waiting: int
    diversification_score: float
    portfolio_health: str
    execution_time: float
    metadata: Mapping[str, object]
