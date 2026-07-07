"""Estrategia simples de rompimento."""

from domain.market_state import MarketState
from strategies.base import Strategy, StrategySignal


class BreakoutStrategy(Strategy):
    """Detecta rompimento perto das extremidades do dia."""

    nome = "breakout"

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Retorna compra ou venda em rompimentos com volume."""
        volume_ok = estado.candle.volume >= 1000
        topo = estado.posicao_no_dia >= 0.8
        fundo = estado.posicao_no_dia <= 0.2

        if volume_ok and topo and estado.direcao == "ALTA":
            return StrategySignal("BUY", 75, 0.75, ["Rompimento de topo"])

        if volume_ok and fundo and estado.direcao == "BAIXA":
            return StrategySignal("SELL", 75, 0.75, ["Rompimento de fundo"])

        return StrategySignal("WAIT", 35, 0.35, ["Sem rompimento valido"])
