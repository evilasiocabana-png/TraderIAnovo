"""Testes do comparador de benchmark da Alpha 001."""

import unittest

from research.alpha001_benchmark_comparator import (
    Alpha001BenchmarkComparator,
    Alpha001BenchmarkResult,
)
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult


class Alpha001BenchmarkComparatorTest(unittest.TestCase):
    """Valida comparacao de resultados agregados de engines Alpha001."""

    def test_compare_retorna_resultado_tipado(self) -> None:
        result = Alpha001BenchmarkComparator().compare([self._research_result()])

        self.assertIsInstance(result, Alpha001BenchmarkResult)

    def test_compare_retorna_resultado_vazio(self) -> None:
        result = Alpha001BenchmarkComparator().compare([])

        self.assertEqual(result.total_results, 0)
        self.assertIsNone(result.best_overall)
        self.assertIsNone(result.best_total_trades)
        self.assertEqual(result.ranking, ())

    def test_compare_identifica_melhor_resultado_geral(self) -> None:
        weak = self._research_result(net_profit=10.0)
        strong = self._research_result(net_profit=100.0)

        result = Alpha001BenchmarkComparator().compare([weak, strong])

        self.assertEqual(result.best_overall, strong)
        self.assertEqual(result.ranking[0], strong)

    def test_compare_identifica_melhores_por_metrica(self) -> None:
        trades = self._research_result(total_trades=20)
        profit = self._research_result(net_profit=120.0)
        drawdown = self._research_result(max_drawdown=5.0)
        factor = self._research_result(profit_factor=3.0)
        win_rate = self._research_result(win_rate=0.8)
        expectancy = self._research_result(expectancy=12.0)

        result = Alpha001BenchmarkComparator().compare(
            [trades, profit, drawdown, factor, win_rate, expectancy]
        )

        self.assertEqual(result.best_total_trades, trades)
        self.assertEqual(result.best_net_profit, profit)
        self.assertEqual(result.best_max_drawdown, drawdown)
        self.assertEqual(result.best_profit_factor, factor)
        self.assertEqual(result.best_win_rate, win_rate)
        self.assertEqual(result.best_expectancy, expectancy)

    def test_compare_nao_recalcula_metricas(self) -> None:
        research_result = self._research_result(
            total_trades=7,
            net_profit=50.0,
            max_drawdown=4.0,
            profit_factor=2.0,
            win_rate=0.7,
            expectancy=8.0,
        )

        result = Alpha001BenchmarkComparator().compare([research_result])

        self.assertEqual(result.best_total_trades.metrics.total_trades, 7)
        self.assertEqual(result.best_net_profit.profit.net_profit_points, 50.0)
        self.assertEqual(result.best_max_drawdown.drawdown.max_drawdown_points, 4.0)
        self.assertEqual(result.best_profit_factor.profit_factor.profit_factor, 2.0)
        self.assertEqual(result.best_win_rate.win_rate.win_rate, 0.7)
        self.assertEqual(result.best_expectancy.expectancy.expectancy, 8.0)

    def test_nao_gera_graficos_dashboard_persistencia_ou_exportacao(self) -> None:
        with open(
            "research/alpha001_benchmark_comparator.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "matplotlib",
            "plot",
            "Dashboard",
            "streamlit",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
            "Broker",
            "MT5",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _research_result(
        self,
        total_trades: int = 1,
        net_profit: float = 10.0,
        max_drawdown: float = 10.0,
        profit_factor: float = 1.0,
        win_rate: float = 0.5,
        expectancy: float = 1.0,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=total_trades,
                total_buy=total_trades,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=max(net_profit, 0.0),
                gross_loss_points=abs(min(net_profit, 0.0)),
                net_profit_points=net_profit,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0, net_profit),
                max_drawdown_points=max_drawdown,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate=win_rate,
            ),
            profit_factor=Alpha001ProfitFactorResult(
                profit_factor=profit_factor,
            ),
            expectancy=Alpha001ExpectancyResult(
                average_win=0.0,
                average_loss=0.0,
                payoff_ratio=0.0,
                expectancy=expectancy,
            ),
        )


if __name__ == "__main__":
    unittest.main()
