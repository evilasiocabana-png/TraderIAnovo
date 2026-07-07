"""Consolidacao de informacoes para tomada de decisao."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from domain.contracts.decision_context import DecisionContext
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from research.research_engine import ResearchResult


@dataclass(frozen=True)
class DecisionAssessment:
    """Consolida insumos usados por componentes de decisao."""

    strategy_signal: StrategySignal
    market_context: MarketContext
    risk_decision: RiskDecision
    research_result: ResearchResult
    decision_context: DecisionContext
    strategy_confidence: float
    market_confidence: float
    research_confidence: float
    risk_status: str
    metadata: Mapping[str, object]
