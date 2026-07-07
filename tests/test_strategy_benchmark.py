"""Testes do benchmark quantitativo de estrategias."""

import unittest

from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from research.strategy_benchmark import (
    StrategyBenchmark,
    StrategyBenchmarkResult,
)


class StaticStrategy:
    """Estrategia fixa para benchmark isolado."""

    nome = "static_buy"

    def analisar(self, estado: object) -> StrategySignal:
        """Retorna sempre compra."""
        return StrategySignal("BUY", 80, 0.8, ["Benchmark"])


class StrategyBenchmarkTest(unittest.TestCase):
    """Valida benchmark isolado de estrategias."""

    def test_run_retorna_resultado_do_benchmark(self) -> None:
        """Garante retorno do DTO de benchmark."""
        result = StrategyBenchmark().run(StaticStrategy(), self._candles())

        self.assertIsInstance(result, StrategyBenchmarkResult)
        self.assertEqual(result.strategy_name, "static_buy")

    def test_run_expoe_metricas_paper(self) -> None:
        """Garante metricas basicas do replay paper."""
        result = StrategyBenchmark().run(StaticStrategy(), self._candles())

        self.assertEqual(result.total_trades, 1)
        self.assertEqual(result.wins, 1)
        self.assertEqual(result.losses, 0)
        self.assertEqual(result.net_profit_points, 100.0)
        self.assertEqual(result.win_rate, 1.0)
        self.assertEqual(result.profit_factor, float("inf"))
        self.assertEqual(result.max_drawdown_points, 0.0)

    def test_run_expoe_equity_curve(self) -> None:
        """Garante curva de patrimonio no resultado."""
        result = StrategyBenchmark().run(StaticStrategy(), self._candles())

        self.assertEqual(result.equity_curve, [0.0, 100.0])

    def test_run_sem_candles_retorna_metricas_zeradas(self) -> None:
        """Garante benchmark vazio sem falhar."""
        result = StrategyBenchmark().run(StaticStrategy(), [])

        self.assertEqual(result.total_trades, 0)
        self.assertEqual(result.equity_curve, [0.0])

    def _candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1000.0, 1000),
            Candle("2026-06-26 09:01", 1000.0, 1100.0, 999.0, 1100.0, 1000),
        ]


if __name__ == "__main__":
    unittest.main()
