"""Entidade de dominio que representa um candle de mercado."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    """Candle OHLCV usado pelas estrategias e pelo backtest."""

    data: str
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    volume: int

    @property
    def amplitude(self) -> float:
        """Retorna a amplitude total do candle."""
        return self.maxima - self.minima

    @property
    def direcao(self) -> str:
        """Classifica a direcao do candle."""
        if self.fechamento > self.abertura:
            return "ALTA"
        if self.fechamento < self.abertura:
            return "BAIXA"
        return "NEUTRO"

    @property
    def corpo(self) -> float:
        """Retorna o tamanho absoluto do corpo do candle."""
        return abs(self.fechamento - self.abertura)
