"""Contrato de snapshot normalizado de mercado."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSnapshot:
    """DTO padrao para contexto de mercado."""

    symbol: str
    datetime: str
    regime: str
    volatility: float
    liquidity: float
    trend_strength: float
    market_dna_score: float
