"""Resumo estatistico consolidado da varredura Alpha 001."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)


@dataclass(frozen=True)
class Alpha001ResearchSummaryResult:
    """Resultado agregado da pesquisa Alpha 001."""

    total_experiments: int
    total_approved: int
    total_rejected: int
    best_profit_factor: float
    lowest_max_drawdown_points: float
    best_net_profit_points: float
    best_configuration: Alpha001ParameterSet | None
    approval_rate: float


@dataclass(frozen=True)
class Alpha001ResearchSummary:
    """Consolida resultados existentes sem executar novas pesquisas."""

    def summarize(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
    ) -> Alpha001ResearchSummaryResult:
        """Gera resumo estatistico da colecao recebida."""
        result_list = list(results)
        if not result_list:
            return self._empty_summary()
        approved = self._approved_count(result_list)
        best_result = self._best_result(result_list)
        return Alpha001ResearchSummaryResult(
            total_experiments=len(result_list),
            total_approved=approved,
            total_rejected=len(result_list) - approved,
            best_profit_factor=max(item.profit_factor for item in result_list),
            lowest_max_drawdown_points=min(
                item.max_drawdown_points for item in result_list
            ),
            best_net_profit_points=max(
                item.net_profit_points for item in result_list
            ),
            best_configuration=best_result.parameters,
            approval_rate=approved / len(result_list),
        )

    def _approved_count(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> int:
        return sum(1 for result in results if result.validation_status == "APPROVED")

    def _best_result(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> Alpha001ParameterSweepResult:
        return max(
            results,
            key=lambda item: (
                item.net_profit_points,
                item.profit_factor,
                -item.max_drawdown_points,
                item.total_trades,
            ),
        )

    def _empty_summary(self) -> Alpha001ResearchSummaryResult:
        return Alpha001ResearchSummaryResult(
            total_experiments=0,
            total_approved=0,
            total_rejected=0,
            best_profit_factor=0.0,
            lowest_max_drawdown_points=0.0,
            best_net_profit_points=0.0,
            best_configuration=None,
            approval_rate=0.0,
        )
