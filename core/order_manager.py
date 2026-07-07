"""Servico responsavel por criar operacoes a partir de sinais."""

from dataclasses import dataclass

from domain.market_state import MarketState
from domain.operacao import Operacao
from strategies.base import StrategySignal


@dataclass(frozen=True)
class OrderManager:
    """Converte sinais em operacoes com stop e gain."""

    stop_pontos: float
    gain_pontos: float

    def criar_operacao(
        self,
        signal: StrategySignal,
        estado: MarketState,
    ) -> Operacao | None:
        """Cria operacao quando o sinal for acionavel."""
        if signal.decisao not in {"COMPRA", "VENDA"}:
            return None

        entrada = estado.preco
        stop, gain = self._calcular_alvos(signal.decisao, entrada)
        return Operacao(signal.decisao, entrada, stop, gain, signal.score, signal.motivo)

    def _calcular_alvos(self, decisao: str, entrada: float) -> tuple[float, float]:
        if decisao == "COMPRA":
            return entrada - self.stop_pontos, entrada + self.gain_pontos
        return entrada + self.stop_pontos, entrada - self.gain_pontos
