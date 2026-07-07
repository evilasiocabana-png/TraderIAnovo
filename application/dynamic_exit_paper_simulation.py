"""Simulacao paper read-only da saida dinamica."""

from __future__ import annotations

from application.dynamic_exit_backtest import DynamicExitBacktestEngine
from domain.contracts.dynamic_exit_backtest import DynamicExitBacktestTrade
from domain.contracts.dynamic_exit_paper import (
    DynamicExitPaperRecommendationRecord,
    DynamicExitPaperSimulationReport,
)


class DynamicExitPaperSimulationEngine:
    """Registra recomendacoes dinamicas e compara resultado paper."""

    def __init__(
        self,
        backtest_engine: DynamicExitBacktestEngine | None = None,
    ) -> None:
        self._backtest_engine = backtest_engine or DynamicExitBacktestEngine()

    def run(
        self,
        records: list[DynamicExitPaperRecommendationRecord],
    ) -> DynamicExitPaperSimulationReport:
        safe_records = [self._readonly_record(record) for record in records]
        if not safe_records:
            return DynamicExitPaperSimulationReport(
                status="SEM_DADOS",
                records=[],
                comparison=self._backtest_engine.run([]),
                message="Nenhuma recomendacao dinamica disponivel para simulacao paper.",
            )

        comparison = self._backtest_engine.run(
            [self._to_backtest_trade(record) for record in safe_records]
        )
        return DynamicExitPaperSimulationReport(
            status="SIMULADO",
            records=safe_records,
            comparison=comparison,
            total_recommendations=len(safe_records),
            simulated_actions=self._action_counts(safe_records),
            message=(
                "Simulacao paper read-only: recomendacoes registradas sem "
                "execucao no Provider Demo."
            ),
        )

    def _readonly_record(
        self,
        record: DynamicExitPaperRecommendationRecord,
    ) -> DynamicExitPaperRecommendationRecord:
        if not record.executed:
            return record
        return DynamicExitPaperRecommendationRecord(
            symbol=record.symbol,
            setup=record.setup,
            timeframe=record.timeframe,
            original_policy=record.original_policy,
            dynamic_action=record.dynamic_action,
            dynamic_reason=record.dynamic_reason,
            dynamic_confidence=record.dynamic_confidence,
            market_state=record.market_state,
            original_result_r=record.original_result_r,
            dynamic_paper_result_r=record.dynamic_paper_result_r,
            original_duration_minutes=record.original_duration_minutes,
            dynamic_duration_minutes=record.dynamic_duration_minutes,
            planned_rr=record.planned_rr,
            executed=False,
        )

    def _to_backtest_trade(
        self,
        record: DynamicExitPaperRecommendationRecord,
    ) -> DynamicExitBacktestTrade:
        return DynamicExitBacktestTrade(
            symbol=record.symbol,
            setup=record.setup,
            timeframe=record.timeframe,
            original_policy=record.original_policy,
            dynamic_action=record.dynamic_action,
            original_result_r=record.original_result_r,
            dynamic_result_r=record.dynamic_paper_result_r,
            original_duration_minutes=record.original_duration_minutes,
            dynamic_duration_minutes=record.dynamic_duration_minutes,
            planned_rr=record.planned_rr,
        )

    def _action_counts(
        self,
        records: list[DynamicExitPaperRecommendationRecord],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            action = str(record.dynamic_action or "N/D").upper()
            counts[action] = counts.get(action, 0) + 1
        return counts
