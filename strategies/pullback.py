"""Estrategia de pullback curto a favor da direcao."""

from domain.market_state import MarketState
from strategies.base import Strategy, StrategySignal


class PullbackStrategy(Strategy):
    """Procura pullbacks curtos em mercados direcionais."""

    nome = "pullback"

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Gera sinal se o pullback estiver curto e controlado."""
        pullback_curto = estado.pullback_pontos <= max(estado.atr * 0.35, 1)
        volume_ok = estado.candle.volume >= 1000

        if pullback_curto and volume_ok and estado.direcao == "ALTA":
            return StrategySignal("BUY", 72, 0.72, ["Pullback curto em alta"])

        if pullback_curto and volume_ok and estado.direcao == "BAIXA":
            return StrategySignal("SELL", 72, 0.72, ["Pullback curto em baixa"])

        return StrategySignal("WAIT", 40, 0.40, ["Pullback sem vantagem clara"])
