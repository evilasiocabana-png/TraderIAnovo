"""Servicos de leitura de volatilidade."""

from dataclasses import dataclass

from domain.candle import Candle


@dataclass(frozen=True)
class VolatilityService:
    """Calcula medidas simples de volatilidade."""

    def true_range(self, candle: Candle) -> float:
        """Calcula range verdadeiro simplificado."""
        return candle.amplitude

    def atr(self, candles: list[Candle], periodo: int = 14) -> float:
        """Calcula ATR simples dos candles informados."""
        amostra = candles[-periodo:]
        if not amostra:
            return 0.0
        total = sum(self.true_range(candle) for candle in amostra)
        return total / len(amostra)
