"""Relatorio textual de backtest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestReport:
    """Formata metricas de backtest para leitura humana."""

    def gerar(self, metricas: dict[str, float]) -> str:
        """Gera relatorio em texto."""
        return (
            f"Total: {metricas.get('total', 0)} | "
            f"Resultado: {metricas.get('resultado', 0):.2f} | "
            f"Taxa de acerto: {metricas.get('taxa_acerto', 0):.0%}"
        )
