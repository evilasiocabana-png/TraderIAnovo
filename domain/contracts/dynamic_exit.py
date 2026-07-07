"""Contrato read-only de recomendacao de saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass


DYNAMIC_EXIT_ACTIONS = (
    "KEEP_ORIGINAL_PLAN",
    "PROTECT_TO_BREAK_EVEN",
    "TRAIL_BY_ATR",
    "TRAIL_BY_STRUCTURE",
    "TIGHTEN_BY_MOMENTUM_LOSS",
    "TIME_DECAY_EXIT_WATCH",
    "NO_ACTION_BAD_CONTEXT",
)

DYNAMIC_EXIT_MARKET_STATES = (
    "NO_POSITION",
    "NEW_POSITION",
    "PROTECTED_POSITION",
    "TREND_RUNNER",
    "REVERSAL_RISK",
    "TIME_DECAY",
    "BAD_EXECUTION_CONTEXT",
)


@dataclass(frozen=True)
class DynamicExitRecommendation:
    """Recomendacao auditavel, sem permissao de execucao demo nesta fase."""

    policy: str = "FIXED_STOP"
    action: str = "KEEP_ORIGINAL_PLAN"
    reason: str = "Saida dinamica read-only ainda sem ajuste operacional."
    confidence: float = 0.0
    market_state: str = "NO_POSITION"
    r_multiple: float = 0.0
    candidate_stop: float | None = None
    allowed_to_execute_demo: bool = False
    source: str = "DYNAMIC_EXIT_READ_ONLY"


@dataclass(frozen=True)
class DynamicExitMarketReading:
    """Leitura read-only do contexto de mercado e posicao."""

    symbol: str = "N/D"
    side: str = "N/D"
    is_positioned: bool = False
    current_price: float | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    atr: float | None = None
    volatility: float | None = None
    momentum: float | None = None
    spread: float | None = None
    time_in_position_minutes: float | None = None
    state: str = "NO_POSITION"
    r_multiple: float = 0.0
    reason: str = "Sem posicao aberta; saida dinamica apenas auditavel."
    candidate_stop: float | None = None
    source: str = "DYNAMIC_EXIT_MARKET_STATE_READ_ONLY"
