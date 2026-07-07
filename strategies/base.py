"""Contratos compartilhados por todas as estrategias."""

from abc import ABC, abstractmethod

from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState


class Strategy(ABC):
    """Interface para estrategias independentes."""

    nome = "base"

    @abstractmethod
    def analisar(self, estado: MarketState) -> StrategySignal:
        """Analisa o estado de mercado e retorna um sinal."""
