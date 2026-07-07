"""Metricas de backtest."""

from dataclasses import dataclass

from domain.operacao import Operacao


@dataclass(frozen=True)
class BacktestMetrics:
    """Calcula metricas basicas do backtest."""

    def calcular(self, operacoes: list[Operacao]) -> dict[str, float]:
        """Retorna metricas agregadas."""
        total = len(operacoes)
        resultado = sum(operacao.resultado for operacao in operacoes)
        acertos = sum(1 for operacao in operacoes if operacao.resultado > 0)
        taxa = acertos / total if total else 0.0
        return {"total": total, "resultado": resultado, "taxa_acerto": taxa}
