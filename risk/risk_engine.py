"""Motor de risco para bloquear sinais sem vantagem operacional."""

from dataclasses import dataclass

from strategies.base import StrategySignal


@dataclass(frozen=True)
class RiskDecision:
    """Resultado da avaliacao de risco."""

    aprovado: bool
    motivo: str


@dataclass
class RiskEngine:
    """Avalia limites financeiros e operacionais."""

    perda_maxima_dia: float
    limite_operacoes: int
    score_minimo: int
    resultado_dia: float = 0.0
    numero_operacoes: int = 0

    def avaliar(self, signal: StrategySignal) -> RiskDecision:
        """Avalia se o sinal pode virar operacao."""
        if self.resultado_dia <= self.perda_maxima_dia:
            return RiskDecision(False, "Perda maxima diaria atingida")

        if self.numero_operacoes >= self.limite_operacoes:
            return RiskDecision(False, "Limite de operacoes atingido")

        if signal.score < self.score_minimo or signal.decisao == "NEUTRO":
            return RiskDecision(False, "Sinal sem score minimo")

        return RiskDecision(True, "Risco aprovado")

    def registrar_resultado(self, resultado: float) -> None:
        """Atualiza o estado de risco apos uma operacao."""
        self.resultado_dia += resultado
        self.numero_operacoes += 1
