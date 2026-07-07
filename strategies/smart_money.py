"""Estrategia baseada em deslocamento e rejeicao de preco."""

from domain.market_state import MarketState
from strategies.base import Strategy, StrategySignal


class SmartMoneyStrategy(Strategy):
    """Leitura inicial de intencao por range, corpo e VWAP."""

    nome = "smart_money"

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Identifica deslocamento relevante acima ou abaixo da VWAP."""
        corpo_forte = estado.candle.corpo >= estado.candle.amplitude * 0.55
        volume_ok = estado.candle.volume >= 1200
        acima_vwap = estado.preco > estado.vwap

        if corpo_forte and volume_ok and acima_vwap:
            return StrategySignal("BUY", 78, 0.78, ["Deslocamento acima da VWAP"])

        if corpo_forte and volume_ok and not acima_vwap:
            return StrategySignal("SELL", 78, 0.78, ["Deslocamento abaixo da VWAP"])

        return StrategySignal("WAIT", 38, 0.38, ["Sem deslocamento institucional"])
