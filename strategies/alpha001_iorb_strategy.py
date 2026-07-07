"""Strategy oficial da Alpha 001 IORB."""

from dataclasses import dataclass, field
from typing import Any, Sequence

from alpha.alpha001_config import Alpha001Config
from alpha.alpha001_decision_engine import Alpha001DecisionEngine
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from strategies.base import Strategy


SCORE_MULTIPLIER = 100


@dataclass
class Alpha001IORBStrategy(Strategy):
    """Adapta Alpha001Decision para o contrato StrategySignal."""

    nome: str = "alpha001_iorb"
    config: Alpha001Config = field(default_factory=Alpha001Config)
    decision_engine: Alpha001DecisionEngine = field(
        default_factory=Alpha001DecisionEngine,
    )

    def generate_signal(
        self,
        candles: Sequence[Any],
        market_snapshot: Any,
        current_price: float,
        minimum_range_size: float | None = None,
        minimum_volume: float | None = None,
        config: Alpha001Config | None = None,
    ) -> StrategySignal:
        """Gera StrategySignal a partir da decisao consolidada da Alpha 001."""
        effective_config = config or self.config
        decision = self.decision_engine.evaluate(
            candles=candles,
            market_snapshot=market_snapshot,
            current_price=current_price,
            minimum_range_size=minimum_range_size,
            minimum_volume=minimum_volume,
            config=effective_config,
        )
        signal_decision = decision.decision if decision.approved else "WAIT"
        score = self._score(decision.confidence)
        reasons = list(decision.reasons)
        if score < effective_config.minimum_score:
            signal_decision = "WAIT"
            reasons.append("score abaixo do minimo")
        if decision.confidence < effective_config.minimum_confidence:
            signal_decision = "WAIT"
            reasons.append("confidence abaixo do minimo")
        return StrategySignal(
            decision=signal_decision,
            score=score,
            confidence=decision.confidence,
            reasons=reasons,
        )

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Retorna WAIT quando usada pela interface basica de Strategy."""
        return StrategySignal(
            decision="WAIT",
            score=0,
            confidence=0.0,
            reasons=["Alpha 001 requer contexto completo via generate_signal"],
        )

    def _score(self, confidence: float) -> int:
        return int(round(confidence * SCORE_MULTIPLIER))
