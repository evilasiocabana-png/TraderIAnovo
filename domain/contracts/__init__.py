"""Contratos DTO para comunicacao interna do dominio."""

from domain.contracts.backtest_result import BacktestResult
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal

__all__ = [
    "BacktestResult",
    "DecisionContext",
    "ExecutionOrder",
    "ExecutionResult",
    "MarketSnapshot",
    "RiskDecision",
    "StrategySignal",
]
