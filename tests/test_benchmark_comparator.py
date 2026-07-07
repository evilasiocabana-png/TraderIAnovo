"""Testes do comparador de benchmarks."""

import unittest

from research.benchmark_comparator import (
    Alpha001BenchmarkComparison,
    BenchmarkComparator,
    BenchmarkComparison,
)
from research.alpha001_experiment import Alpha001ExperimentResult
from research.strategy_benchmark import StrategyBenchmarkResult


class BenchmarkComparatorTest(unittest.TestCase):
    """Valida comparacao isolada de benchmarks."""

    def test_compare_sem_benchmarks_retorna_vazio(self) -> None:
        """Garante retorno vazio quando nao ha benchmarks."""
        comparison = BenchmarkComparator().compare([])

        self.assertIsInstance(comparison, BenchmarkComparison)
        self.assertIsNone(comparison.best_strategy)
        self.assertEqual(comparison.best_profit, 0.0)
        self.assertEqual(comparison.best_profit_factor, 0.0)
        self.assertEqual(comparison.best_drawdown, 0.0)
        self.assertEqual(comparison.best_win_rate, 0.0)
        self.assertEqual(comparison.ranking, [])

    def test_compare_ordena_por_net_profit(self) -> None:
        """Garante ordenacao inicial por lucro liquido."""
        low = self._benchmark("low", net_profit_points=10.0)
        high = self._benchmark("high", net_profit_points=20.0)

        comparison = BenchmarkComparator().compare([low, high])

        self.assertEqual(comparison.best_strategy, "high")
        self.assertEqual(comparison.ranking, [high, low])

    def test_compare_desempata_por_profit_factor(self) -> None:
        """Garante desempate por profit factor."""
        weak = self._benchmark(
            "weak",
            net_profit_points=20.0,
            profit_factor=1.5,
        )
        strong = self._benchmark(
            "strong",
            net_profit_points=20.0,
            profit_factor=2.0,
        )

        comparison = BenchmarkComparator().compare([weak, strong])

        self.assertEqual(comparison.best_strategy, "strong")
        self.assertEqual(comparison.ranking, [strong, weak])

    def test_compare_desempata_por_win_rate(self) -> None:
        """Garante desempate por taxa de acerto."""
        lower = self._benchmark(
            "lower",
            net_profit_points=20.0,
            profit_factor=2.0,
            win_rate=0.4,
        )
        higher = self._benchmark(
            "higher",
            net_profit_points=20.0,
            profit_factor=2.0,
            win_rate=0.7,
        )

        comparison = BenchmarkComparator().compare([lower, higher])

        self.assertEqual(comparison.best_strategy, "higher")
        self.assertEqual(comparison.ranking, [higher, lower])

    def test_compare_expoe_metricas_do_melhor(self) -> None:
        """Garante campos agregados do melhor benchmark."""
        best = self._benchmark(
            "best",
            net_profit_points=30.0,
            profit_factor=3.0,
            max_drawdown_points=5.0,
            win_rate=0.8,
        )

        comparison = BenchmarkComparator().compare([best])

        self.assertEqual(comparison.best_strategy, "best")
        self.assertEqual(comparison.best_profit, 30.0)
        self.assertEqual(comparison.best_profit_factor, 3.0)
        self.assertEqual(comparison.best_drawdown, 5.0)
        self.assertEqual(comparison.best_win_rate, 0.8)

    def test_compare_alpha001_retorna_relatorio_tipado(self) -> None:
        """Comparacao Alpha 001 estrutural deve retornar DTO tipado."""
        comparison = BenchmarkComparator().compare_alpha001(
            self._alpha_result(total_signals=1),
            self._alpha_result(total_signals=2),
            left_label="base",
            right_label="candidate",
        )

        self.assertIsInstance(comparison, Alpha001BenchmarkComparison)
        self.assertEqual(comparison.best_label, "candidate")

    def test_compare_alpha001_nao_compara_metricas_financeiras(self) -> None:
        """Resultado inicial da Alpha 001 nao possui metricas financeiras."""
        comparison = BenchmarkComparator().compare_alpha001(
            self._alpha_result(total_signals=1),
            self._alpha_result(total_signals=4),
        )

        self.assertEqual(comparison.profit_factor_delta, 0.0)
        self.assertEqual(comparison.win_rate_delta, 0.0)
        self.assertEqual(comparison.drawdown_delta, 0.0)
        self.assertEqual(comparison.net_profit_delta, 0.0)
        self.assertEqual(comparison.total_trades_delta, 3)

    def test_compare_alpha001_empate_retorna_sem_melhor(self) -> None:
        """Resultados equivalentes nao devem eleger vencedor artificial."""
        result = self._alpha_result(total_signals=1)

        comparison = BenchmarkComparator().compare_alpha001(result, result)

        self.assertIsNone(comparison.best_label)

    def _benchmark(
        self,
        strategy_name: str,
        net_profit_points: float = 0.0,
        profit_factor: float = 0.0,
        max_drawdown_points: float = 0.0,
        win_rate: float = 0.0,
    ) -> StrategyBenchmarkResult:
        return StrategyBenchmarkResult(
            strategy_name=strategy_name,
            total_trades=1,
            wins=1,
            losses=0,
            net_profit_points=net_profit_points,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_points=max_drawdown_points,
            equity_curve=[0.0, net_profit_points],
        )

    def _alpha_result(
        self,
        total_signals: int = 1,
    ) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=total_signals,
            total_signals=total_signals,
            total_buy=total_signals,
            total_sell=0,
            total_wait=0,
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
