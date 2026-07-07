"""Estatisticas operacionais de sinais e operacoes."""

from dataclasses import dataclass

from domain.operacao import Operacao


@dataclass(frozen=True)
class EstatisticasOperacionais:
    """Calcula indicadores simples de desempenho."""

    def total_operacoes(self, operacoes: list[Operacao]) -> int:
        """Retorna a quantidade de operacoes."""
        return len(operacoes)

    def taxa_acerto(self, operacoes: list[Operacao]) -> float:
        """Calcula percentual de operacoes positivas."""
        fechadas = [operacao for operacao in operacoes if operacao.status == "FECHADA"]
        if not fechadas:
            return 0.0
        ganhos = sum(1 for operacao in fechadas if operacao.resultado > 0)
        return ganhos / len(fechadas)

    def resultado_total(self, operacoes: list[Operacao]) -> float:
        """Soma o resultado financeiro das operacoes."""
        return sum(operacao.resultado for operacao in operacoes)
