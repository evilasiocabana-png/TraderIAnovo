"""Contrato de contexto final de decisao."""

from dataclasses import dataclass

from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


@dataclass(frozen=True)
class DecisionContext:
    """DTO que centraliza sinal, mercado, risco e decisao final."""

    strategy_signal: StrategySignal
    market_snapshot: MarketSnapshot
    risk_decision: RiskDecision
    final_decision: str
    final_confidence: float
    approved: bool
