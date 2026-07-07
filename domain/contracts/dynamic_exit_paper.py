"""Contratos read-only para simulacao paper de saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.contracts.dynamic_exit_backtest import (
    DynamicExitBacktestComparisonReport,
)


@dataclass(frozen=True)
class DynamicExitPaperRecommendationRecord:
    """Registro de uma recomendacao dinamica observada em paper."""

    symbol: str
    setup: str
    timeframe: str
    original_policy: str
    dynamic_action: str
    dynamic_reason: str
    dynamic_confidence: float
    market_state: str
    original_result_r: float
    dynamic_paper_result_r: float
    original_duration_minutes: float = 0.0
    dynamic_duration_minutes: float = 0.0
    planned_rr: float = 0.0
    executed: bool = False


@dataclass(frozen=True)
class DynamicExitPaperSimulationReport:
    """Relatorio consolidado da simulacao paper de saida dinamica."""

    status: str
    records: list[DynamicExitPaperRecommendationRecord] = field(default_factory=list)
    comparison: DynamicExitBacktestComparisonReport | None = None
    total_recommendations: int = 0
    simulated_actions: dict[str, int] = field(default_factory=dict)
    read_only: bool = True
    execution_allowed: bool = False
    message: str = "Simulacao paper read-only da saida dinamica."
