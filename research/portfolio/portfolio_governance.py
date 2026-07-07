"""Regras oficiais de governanca do portfolio quantitativo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioGovernance:
    """Representa parametros institucionais de governanca do portfolio."""

    maximum_alphas: int
    maximum_per_family: int
    minimum_diversification: float
    maximum_correlation: float
    minimum_validation_level: str
    minimum_benchmark_score: float
