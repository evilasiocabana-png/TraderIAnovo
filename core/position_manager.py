"""Gerenciamento de posicao aberta."""

from dataclasses import dataclass

from domain.operacao import Operacao


@dataclass
class PositionManager:
    """Mantem a posicao corrente em memoria."""

    posicao_atual: Operacao | None = None

    def abrir(self, operacao: Operacao) -> None:
        """Abre uma nova posicao."""
        self.posicao_atual = operacao

    def fechar(self, resultado: float) -> Operacao | None:
        """Fecha a posicao atual e retorna a operacao."""
        if self.posicao_atual is None:
            return None

        operacao = self.posicao_atual
        operacao.status = "FECHADA"
        operacao.resultado = resultado
        self.posicao_atual = None
        return operacao

    def tem_posicao(self) -> bool:
        """Informa se existe posicao aberta."""
        return self.posicao_atual is not None
