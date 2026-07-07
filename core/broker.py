"""Abstracao de broker para execucao de operacoes."""

from dataclasses import dataclass, field

from domain.operacao import Operacao


@dataclass
class SimulatedBroker:
    """Broker em memoria usado por simulacao e backtest."""

    operacoes: list[Operacao] = field(default_factory=list)

    def enviar_ordem(self, operacao: Operacao) -> Operacao:
        """Registra uma operacao como enviada."""
        self.operacoes.append(operacao)
        return operacao
