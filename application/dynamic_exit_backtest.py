"""Backtest read-only da saida dinamica."""

from __future__ import annotations

from domain.contracts.dynamic_exit_backtest import (
    DynamicExitBacktestComparisonReport,
    DynamicExitBacktestMetrics,
    DynamicExitBacktestTrade,
)


class DynamicExitBacktestEngine:
    """Compara saida original do Lab contra recomendacao dinamica."""

    def run(
        self,
        trades: list[DynamicExitBacktestTrade],
    ) -> DynamicExitBacktestComparisonReport:
        if not trades:
            empty = DynamicExitBacktestMetrics()
            return DynamicExitBacktestComparisonReport(
                status="SEM_DADOS",
                original=empty,
                dynamic=empty,
                message="Nenhuma amostra disponivel para backtest read-only.",
            )

        original_results = [float(trade.original_result_r) for trade in trades]
        dynamic_results = [float(trade.dynamic_result_r) for trade in trades]
        original_durations = [
            float(trade.original_duration_minutes) for trade in trades
        ]
        dynamic_durations = [
            float(trade.dynamic_duration_minutes) for trade in trades
        ]
        planned_rr = [float(trade.planned_rr) for trade in trades]

        original = self._metrics(original_results, original_durations, planned_rr)
        dynamic = self._metrics(dynamic_results, dynamic_durations, planned_rr)
        return DynamicExitBacktestComparisonReport(
            status="COMPARADO",
            original=original,
            dynamic=dynamic,
            break_even_dominance=self._break_even_dominance(trades),
            lost_gain_by_early_exit_r=self._lost_gain_by_early_exit(
                original_results,
                dynamic_results,
            ),
            loss_protection_r=self._loss_protection(
                original_results,
                dynamic_results,
            ),
            winner=self._winner(original, dynamic),
            message=(
                "Comparacao read-only: saida original do Lab versus "
                "recomendacao dinamica."
            ),
        )

    def _metrics(
        self,
        results: list[float],
        durations: list[float],
        planned_rr: list[float],
    ) -> DynamicExitBacktestMetrics:
        total = len(results)
        if total == 0:
            return DynamicExitBacktestMetrics()

        return DynamicExitBacktestMetrics(
            total_trades=total,
            net_profit_r=sum(results),
            max_drawdown_r=self._max_drawdown(results),
            win_rate=sum(1 for result in results if result > 0.0) / total,
            profit_factor=self._profit_factor(results),
            expectancy_r=sum(results) / total,
            average_duration_minutes=sum(durations) / total,
            average_rr=sum(planned_rr) / total,
        )

    def _max_drawdown(self, results: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for result in results:
            equity += result
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    def _profit_factor(self, results: list[float]) -> float:
        gross_profit = sum(result for result in results if result > 0.0)
        gross_loss = abs(sum(result for result in results if result < 0.0))
        if gross_loss == 0.0:
            return gross_profit if gross_profit > 0.0 else 0.0
        return gross_profit / gross_loss

    def _break_even_dominance(
        self,
        trades: list[DynamicExitBacktestTrade],
    ) -> float:
        if not trades:
            return 0.0
        break_even_count = sum(
            1
            for trade in trades
            if "BREAK_EVEN" in trade.original_policy.upper()
            or trade.dynamic_action.upper() == "PROTECT_TO_BREAK_EVEN"
            or abs(float(trade.dynamic_result_r)) <= 0.05
        )
        return break_even_count / len(trades)

    def _lost_gain_by_early_exit(
        self,
        original_results: list[float],
        dynamic_results: list[float],
    ) -> float:
        return sum(
            max(0.0, original - dynamic)
            for original, dynamic in zip(original_results, dynamic_results)
        )

    def _loss_protection(
        self,
        original_results: list[float],
        dynamic_results: list[float],
    ) -> float:
        return sum(
            max(0.0, dynamic - original)
            for original, dynamic in zip(original_results, dynamic_results)
            if original < 0.0
        )

    def _winner(
        self,
        original: DynamicExitBacktestMetrics,
        dynamic: DynamicExitBacktestMetrics,
    ) -> str:
        if dynamic.net_profit_r > original.net_profit_r:
            return "DYNAMIC_EXIT"
        if original.net_profit_r > dynamic.net_profit_r:
            return "ORIGINAL_LAB_EXIT"
        if dynamic.max_drawdown_r < original.max_drawdown_r:
            return "DYNAMIC_EXIT"
        if original.max_drawdown_r < dynamic.max_drawdown_r:
            return "ORIGINAL_LAB_EXIT"
        return "TIE"
