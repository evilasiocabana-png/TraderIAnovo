"""Contrato de resultado consolidado de backtest."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestResult:
    """DTO padrao para metricas finais de backtest."""

    total_profit: float
    total_trades: int
    win_rate: float
    drawdown: float
    profit_factor: float
    sharpe: float
