"""Modelo oficial de hipotese quantitativa."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class AlphaHypothesis:
    """Representa uma hipotese quantitativa sem executar pesquisa."""

    hypothesis_id: str
    alpha_name: str
    version: int
    title: str
    description: str
    market: str
    timeframe: str
    context: str
    trigger: str
    expected_behavior: str
    risk_assumptions: tuple[str, ...]
    validation_plan: str
    author: str
    created_at: datetime
    status: str
    formal_hypothesis: str = ""
    allowed_markets: tuple[str, ...] = field(default_factory=tuple)
    forbidden_markets: tuple[str, ...] = field(default_factory=tuple)
    used_layers: tuple[str, ...] = field(default_factory=tuple)
    searchable_parameters: tuple[str, ...] = field(default_factory=tuple)
    rejection_criteria: tuple[str, ...] = field(default_factory=tuple)
    approval_criteria: tuple[str, ...] = field(default_factory=tuple)
