"""Calculo reutilizavel de curva de equity e drawdown."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EquityDrawdownResult:
    """Resultado da analise de curva de equity."""

    equity_curve: tuple[float, ...]
    peak_equity: float
    max_drawdown_points: float


@dataclass(frozen=True)
class EquityDrawdownCalculator:
    """Calcula curva acumulada, pico e drawdown maximo."""

    def calculate(self, trade_results: Iterable[float]) -> EquityDrawdownResult:
        """Calcula drawdown a partir de resultados de trades fechados."""
        equity = 0.0
        peak_equity = 0.0
        max_drawdown_points = 0.0
        equity_curve = [0.0]

        for trade_result in trade_results:
            equity += float(trade_result)
            equity_curve.append(equity)
            peak_equity = max(peak_equity, equity)
            max_drawdown_points = max(max_drawdown_points, peak_equity - equity)

        return EquityDrawdownResult(
            equity_curve=tuple(equity_curve),
            peak_equity=peak_equity,
            max_drawdown_points=max_drawdown_points,
        )
