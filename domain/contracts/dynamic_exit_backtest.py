"""Contratos read-only para backtest de saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicExitBacktestTrade:
    """Amostra comparativa entre saida original do Lab e saida dinamica."""

    symbol: str
    setup: str
    timeframe: str
    original_policy: str
    dynamic_action: str
    original_result_r: float
    dynamic_result_r: float
    original_duration_minutes: float = 0.0
    dynamic_duration_minutes: float = 0.0
    planned_rr: float = 0.0


@dataclass(frozen=True)
class DynamicExitBacktestMetrics:
    """Metricas agregadas de uma perna do comparativo."""

    total_trades: int = 0
    net_profit_r: float = 0.0
    max_drawdown_r: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy_r: float = 0.0
    average_duration_minutes: float = 0.0
    average_rr: float = 0.0


@dataclass(frozen=True)
class DynamicExitBacktestComparisonReport:
    """Relatorio read-only comparando plano original e saida dinamica."""

    status: str
    original: DynamicExitBacktestMetrics
    dynamic: DynamicExitBacktestMetrics
    break_even_dominance: float = 0.0
    lost_gain_by_early_exit_r: float = 0.0
    loss_protection_r: float = 0.0
    winner: str = "TIE"
    read_only: bool = True
    execution_allowed: bool = False
    message: str = "Backtest read-only de saida dinamica."
