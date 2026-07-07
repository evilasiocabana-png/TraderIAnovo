"""Contrato oficial de candidata ao portfolio quantitativo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.validation.suite.validation_certification import (
    ValidationCertificationResult,
)


@dataclass(frozen=True)
class PortfolioCandidate:
    """Representa uma Alpha candidata ao portfolio quantitativo."""

    candidate_id: str
    alpha_id: str
    benchmark_result: AlphaBenchmarkResult
    validation_certification: ValidationCertificationResult
    portfolio_score: float
    current_status: str
    created_at: str
    metadata: Mapping[str, object]
