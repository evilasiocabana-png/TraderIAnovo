"""Testes do analisador de performance por regime."""

import unittest

from domain.contracts.backtest_result import BacktestResult
from research.regime_performance_analyzer import (
    RegimeBacktestResult,
    RegimePerformanceAnalysis,
    RegimePerformanceAnalyzer,
    RegimePerformanceReport,
)


class RegimePerformanceAnalyzerTest(unittest.TestCase):
    """Valida analise usando apenas BacktestResult existentes."""

    def test_consolida_metricas_por_regime(self) -> None:
        """Resultados do mesmo regime devem ser agregados."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [
                self._entry("TREND", total_profit=100.0, trades=10),
                self._entry("TREND", total_profit=50.0, trades=5),
            ]
        )

        report = analysis.reports[0]
        self.assertEqual(report.regime, "TREND")
        self.assertEqual(report.metrics.total_trades, 15)
        self.assertEqual(report.metrics.net_profit_points, 150.0)

    def test_identifica_melhor_regime(self) -> None:
        """Melhor regime deve ter maior ranking de performance."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [
                self._entry("RANGE", total_profit=-20.0, profit_factor=0.8),
                self._entry("TREND", total_profit=120.0, profit_factor=1.8),
            ]
        )

        self.assertEqual(analysis.best_regime, "TREND")

    def test_identifica_pior_regime(self) -> None:
        """Pior regime deve ficar no menor ranking de performance."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [
                self._entry("BREAKOUT", total_profit=80.0, profit_factor=1.4),
                self._entry("RANGE", total_profit=-30.0, profit_factor=0.7),
            ]
        )

        self.assertEqual(analysis.worst_regime, "RANGE")

    def test_valida_retorno_regime_performance_report(self) -> None:
        """Analyzer deve retornar relatorios tipados."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [self._entry("TREND", total_profit=100.0)]
        )

        self.assertIsInstance(analysis, RegimePerformanceAnalysis)
        self.assertIsInstance(analysis.reports[0], RegimePerformanceReport)

    def test_calcula_win_rate_ponderado_por_trades(self) -> None:
        """Win rate consolidado deve respeitar tamanho da amostra."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [
                self._entry("TREND", win_rate=1.0, trades=10),
                self._entry("TREND", win_rate=0.0, trades=30),
            ]
        )

        self.assertEqual(analysis.reports[0].metrics.win_rate, 0.25)

    def test_recommendation_favorable_regime(self) -> None:
        """Regime lucrativo com PF bom deve ser favoravel."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [self._entry("TREND", total_profit=100.0, profit_factor=1.5)]
        )

        self.assertEqual(analysis.reports[0].recommendation, "FAVORABLE_REGIME")

    def test_recommendation_avoid_regime(self) -> None:
        """Regime negativo deve ser evitado."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [self._entry("RANGE", total_profit=-20.0, profit_factor=0.8)]
        )

        self.assertEqual(analysis.reports[0].recommendation, "AVOID_REGIME")

    def test_regime_invalido_vira_unknown(self) -> None:
        """Regimes fora da lista oficial devem virar UNKNOWN."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [self._entry("qualquer", total_profit=10.0)]
        )

        self.assertEqual(analysis.reports[0].regime, "UNKNOWN")

    def test_aceita_dict_com_backtest_result(self) -> None:
        """Analyzer deve aceitar entrada em dict."""
        analysis = RegimePerformanceAnalyzer().analyze(
            [
                {
                    "regime": "REVERSAL",
                    "backtest_result": self._backtest(total_profit=40.0),
                }
            ]
        )

        self.assertEqual(analysis.reports[0].regime, "REVERSAL")

    def test_lista_vazia_retorna_analysis_seguro(self) -> None:
        """Sem resultados nao deve quebrar."""
        analysis = RegimePerformanceAnalyzer().analyze([])

        self.assertEqual(analysis.reports, [])
        self.assertIsNone(analysis.best_regime)
        self.assertIsNone(analysis.worst_regime)

    def _entry(
        self,
        regime: str,
        total_profit: float = 0.0,
        trades: int = 10,
        win_rate: float = 0.6,
        drawdown: float = 10.0,
        profit_factor: float = 1.4,
    ) -> RegimeBacktestResult:
        return RegimeBacktestResult(
            regime=regime,
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
