"""Estado de mercado enriquecido para tomada de decisao."""

from dataclasses import dataclass

from domain.candle import Candle


@dataclass(frozen=True)
class MarketState:
    """Snapshot contextual usado por estrategias, risco e MARKET DNA."""

    candle: Candle
    vwap: float
    atr: float
    pullback_pontos: float
    horario: int
    resultado_operacao: float | None = None
    observacao: str = ""

    @property
    def preco(self) -> float:
        """Retorna o preco atual do estado."""
        return self.candle.fechamento

    @property
    def posicao_no_dia(self) -> float:
        """Retorna a posicao relativa do preco dentro da amplitude."""
        if self.candle.amplitude <= 0:
            return 0.5
        distancia = self.preco - self.candle.minima
        return distancia / self.candle.amplitude

    @property
    def direcao(self) -> str:
        """Delegacao da direcao do candle."""
        return self.candle.direcao
