"""Relatorio oficial de benchmark entre Alphas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_dominance_engine import AlphaDominanceResult
from research.benchmark.alpha_similarity_engine import AlphaSimilarityResult


@dataclass(frozen=True)
class AlphaBenchmarkReport:
    """Consolida resultados de benchmark sem realizar calculos."""

    benchmark_result: AlphaBenchmarkResult
    dominance: AlphaDominanceResult
    similarity: AlphaSimilarityResult
    alpha_a: str
    alpha_b: str
    benchmark_summary: str
    dominance_result: str
    similarity_score: float
    diversification_score: float
    recommendation: str
    execution_time: float
    metadata: Mapping[str, object]
