"""Servicos de leitura de volume."""

from dataclasses import dataclass

from domain.candle import Candle


@dataclass(frozen=True)
class VolumeService:
    """Classifica volume relativo do mercado."""

    volume_minimo: int = 1000

    def classificar(self, candle: Candle) -> str:
        """Classifica o volume do candle."""
        if candle.volume >= self.volume_minimo * 1.5:
            return "FORTE"
        if candle.volume >= self.volume_minimo:
            return "NORMAL"
        return "BAIXO"

    def media(self, candles: list[Candle]) -> float:
        """Calcula volume medio."""
        if not candles:
            return 0.0
        return sum(candle.volume for candle in candles) / len(candles)
