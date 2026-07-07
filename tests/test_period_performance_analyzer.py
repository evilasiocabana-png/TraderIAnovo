"""Testes do analisador de performance por periodo."""

import unittest

from domain.contracts.backtest_result import BacktestResult
from research.period_performance_analyzer import (
    PeriodBacktestResult,
    PeriodPerformanceAnalysis,
    PeriodPerformanceAnalyzer,
    PeriodPerformanceReport,
)


class PeriodPerformanceAnalyzerTest(unittest.TestCase):
    """Valida analise temporal usando BacktestResult existentes."""

    def test_consolida_metricas_por_dia(self) -> None:
        """Resultados do mesmo dia devem ser agregados."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-26", total_profit=100.0, trades=10),
                self._entry("2026-06-26 10:00", total_profit=50.0, trades=5),
            ],
            "DAY",
        )

        report = analysis.reports[0]
        self.assertEqual(report.period, "2026-06-26")
        self.assertEqual(report.metrics.total_trades, 15)
        self.assertEqual(report.metrics.net_profit_points, 150.0)

    def test_consolida_metricas_por_semana(self) -> None:
        """Resultados da mesma semana ISO devem ser agregados."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-22", total_profit=20.0),
                self._entry("2026-06-26", total_profit=30.0),
            ],
            "WEEK",
        )

        self.assertEqual(len(analysis.reports), 1)
        self.assertEqual(analysis.reports[0].period, "2026-W26")
        self.assertEqual(analysis.reports[0].metrics.net_profit_points, 50.0)

    def test_consolida_metricas_por_mes(self) -> None:
        """Resultados do mesmo mes devem ser agregados."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-01", total_profit=20.0),
                self._entry("2026-06-26", total_profit=30.0),
            ],
            "MONTH",
        )

        self.assertEqual(len(analysis.reports), 1)
        self.assertEqual(analysis.reports[0].period, "2026-06")

    def test_identifica_melhor_periodo(self) -> None:
        """Melhor periodo deve vir do maior ranking de performance."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-26", total_profit=-20.0, profit_factor=0.8),
                self._entry("2026-06-27", total_profit=120.0, profit_factor=1.8),
            ],
            "DAY",
        )

        self.assertEqual(analysis.best_period, "2026-06-27")

    def test_identifica_pior_periodo(self) -> None:
        """Pior periodo deve vir do menor ranking de performance."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-26", total_profit=80.0, profit_factor=1.4),
                self._entry("2026-06-27", total_profit=-30.0, profit_factor=0.7),
            ],
            "DAY",
        )

        self.assertEqual(analysis.worst_period, "2026-06-27")

    def test_calcula_win_rate_ponderado_por_trades(self) -> None:
        """Win rate consolidado deve respeitar quantidade de trades."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                self._entry("2026-06-26", win_rate=1.0, trades=10),
                self._entry("2026-06-26", win_rate=0.0, trades=30),
            ],
            "DAY",
        )

        self.assertEqual(analysis.reports[0].metrics.win_rate, 0.25)

    def test_valida_retorno_period_performance_report(self) -> None:
        """Analyzer deve retornar DTOs tipados."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [self._entry("2026-06-26", total_profit=100.0)],
            "DAY",
        )

        self.assertIsInstance(analysis, PeriodPerformanceAnalysis)
        self.assertIsInstance(analysis.reports[0], PeriodPerformanceReport)

    def test_aceita_dict_com_backtest_result(self) -> None:
        """Analyzer deve aceitar entrada em dict."""
        analysis = PeriodPerformanceAnalyzer().analyze(
            [
                {
                    "date": "2026-06-26",
                    "backtest_result": self._backtest(total_profit=40.0),
                }
            ],
            "DAY",
        )

        self.assertEqual(analysis.reports[0].period, "2026-06-26")

    def test_periodo_invalido_gera_erro(self) -> None:
        """Periodo fora da lista oficial deve ser rejeitado."""
        with self.assertRaises(ValueError):
            PeriodPerformanceAnalyzer().analyze([], "YEAR")

    def test_lista_vazia_retorna_analysis_seguro(self) -> None:
        """Sem resultados nao deve quebrar."""
        analysis = PeriodPerformanceAnalyzer().analyze([], "DAY")

        self.assertEqual(analysis.reports, [])
        self.assertIsNone(analysis.best_period)
        self.assertIsNone(analysis.worst_period)

    def _entry(
        self,
        date: str,
        total_profit: float = 0.0,
        trades: int = 10,
        win_rate: float = 0.6,
        drawdown: float = 10.0,
        profit_factor: float = 1.4,
    ) -> PeriodBacktestResult:
        return PeriodBacktestResult(
            date=date,
            backtest_result=self._backtest(
                total_profit=total_profit,
                trades=trades,
                win_rate=win_rate,
                drawdown=drawdown,
                profit_factor=profit_factor,
            ),
        )

    def _backtest(
        self,
        total_profit: float = 0.0,
        trades: int = 10,
        win_rate: float = 0.6,
        drawdown: float = 10.0,
        profit_factor: float = 1.4,
    ) -> BacktestResult:
        return BacktestResult(
            total_profit=total_profit,
            total_trades=trades,
            win_rate=win_rate,
            drawdown=drawdown,
            profit_factor=profit_factor,
            sharpe=0.0,
        )


if __name__ == "__main__":
    unittest.main()
