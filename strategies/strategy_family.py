"""Classificacao oficial das familias de estrategia."""

from enum import Enum


class StrategyFamily(Enum):
    """Representa apenas a familia de uma estrategia."""

    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITION = "POSITION"
    LONG_SHORT = "LONG_SHORT"
    PORTFOLIO = "PORTFOLIO"
