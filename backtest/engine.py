"""Motor de backtest independente da infraestrutura."""

from dataclasses import dataclass, field

from core.engine import TradingEngine
from domain.market_state import MarketState
from domain.operacao import Operacao


@dataclass
class BacktestResult:
    """Resultado de uma execucao de backtest."""

    operacoes: list[Operacao] = field(default_factory=list)


@dataclass
class BacktestEngine:
    """Executa uma sequencia de estados no motor de trading."""

    engine: TradingEngine

    def executar(self, estados: list[MarketState]) -> BacktestResult:
        """Processa todos os estados e coleta operacoes."""
        resultado = BacktestResult()
        for estado in estados:
            operacao = self.engine.processar(estado)
            if operacao is not None:
                resultado.operacoes.append(operacao)
        return resultado
