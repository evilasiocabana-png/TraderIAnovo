"""Relatorio oficial do Context Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from market.context.context_quality_engine import ContextQualityResult
from market.context.market_context import MarketContext


@dataclass(frozen=True)
class ContextReport:
    """Consolida resultados produzidos pelo Context Lab."""

    context: MarketContext
    quality_result: ContextQualityResult
    regime: str
    volatility: float
    liquidity: float
    momentum: float
    session: str
    market_dna: Mapping[str, object]
    confidence_score: float
    quality_score: float
    execution_time: float
