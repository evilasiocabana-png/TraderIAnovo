"""Contrato oficial de perfil de risco."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RiskProfile:
    """Representa uma politica parametrizada de risco."""

    capital: float
    max_exposure: float
    risk_per_trade: float
    daily_risk_limit: float
    max_daily_loss: float
    max_daily_gain: float
    max_drawdown_allowed: float
    contracts: int
    enabled: bool
    metadata: Mapping[str, object]
