"""Pipeline central de tomada de decisao."""

from dataclasses import dataclass

from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


@dataclass(frozen=True)
class DecisionPipeline:
    """Centraliza a composicao da decisao final."""

    def processar(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        risk_decision: RiskDecision,
    ) -> DecisionContext:
        """Monta o contexto final sem alterar a decisao."""
        return DecisionContext(
            strategy_signal=strategy_signal,
            market_snapshot=market_snapshot,
            risk_decision=risk_decision,
            final_decision=strategy_signal.decision,
            final_confidence=strategy_signal.confidence,
            approved=risk_decision.allowed,
        )
