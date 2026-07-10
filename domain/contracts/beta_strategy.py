"""Contratos para estrategias Beta de gestao pos-entrada."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class BetaStrategyContext:
    """Contexto operacional leve entregue pelo Position Manager."""

    symbol: str
    ticket: int
    side: str
    volume: float
    entry_price: float
    current_price: float
    current_stop: float
    current_target: float | None
    current_r: float
    candles: tuple[object, ...] = ()
    position_open: bool = True
    candle_closed: bool = False
    evaluated_at: str = "N/D"
    previous_state: str = "N/D"
    previous_confirmation_count: int = 0
    previous_state_duration: int = 0
    previous_action_key: str = "N/D"
    stop_management_parameters: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BetaDecision:
    """Decisao auditavel retornada por uma estrategia Beta."""

    beta_id: str
    beta_version: str
    state: str
    raw_state: str
    action: str
    reason: str
    strength_score: float
    confirmation_count: int
    state_duration: int
    candidate_stop: float | None
    current_r: float
    ema14_value: float | None
    ema14_slope: float | None
    momentum_14: float | None
    atr_14: float | None
    atr_relative_change: float | None
    structure_signal: str
    evaluated_at: str
    evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    final_exit_reason: str = "N/D"
    missing_data: tuple[str, ...] = ()


class BetaStrategy(Protocol):
    """Interface unica para estrategias Beta."""

    beta_id: str
    beta_version: str

    def evaluate(self, context: BetaStrategyContext) -> BetaDecision:
        """Avalia uma posicao aberta e retorna decisao auditavel."""
