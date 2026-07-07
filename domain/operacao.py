"""Entidade de dominio que representa uma operacao planejada ou executada."""

from dataclasses import dataclass


@dataclass
class Operacao:
    """Operacao com entrada, risco, alvo e resultado financeiro."""

    tipo: str
    entrada: float
    stop: float
    gain: float
    score: int
    motivo: str
    status: str = "ABERTA"
    resultado: float = 0.0

    @property
    def risco_pontos(self) -> float:
        """Calcula a distancia da entrada ate o stop."""
        return abs(self.entrada - self.stop)

    @property
    def ganho_pontos(self) -> float:
        """Calcula a distancia da entrada ate o alvo."""
        return abs(self.gain - self.entrada)
