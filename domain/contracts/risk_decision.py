"""Contrato de decisao de risco."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    """DTO padrao para resposta do motor de risco."""

    allowed: bool
    reason: str
    max_contracts: float
    risk_multiplier: float
