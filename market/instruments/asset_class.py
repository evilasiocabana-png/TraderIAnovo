"""Classificacao oficial das classes de ativos."""

from enum import Enum


class AssetClass(Enum):
    """Representa apenas a classe de um ativo financeiro."""

    FUTURES = "FUTURES"
    STOCKS = "STOCKS"
    ETF = "ETF"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    COMMODITIES = "COMMODITIES"
    FIXED_INCOME = "FIXED_INCOME"
