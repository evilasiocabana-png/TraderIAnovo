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
