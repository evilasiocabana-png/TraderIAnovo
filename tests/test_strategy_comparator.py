"""Testes do comparador de estrategias do Research Lab."""

import unittest

from domain.contracts.backtest_result import BacktestResult
from research.strategy_benchmark import StrategyBenchmarkResult
from research.strategy_comparator import (
    StrategyComparator,
    StrategyComparisonEntry,
    StrategyComparisonResult,
)


class StrategyComparatorTest(unittest.TestCase):
    """Valida comparacao entre estrategias sem executar experimentos."""

    def test_compara_duas_estrategias_e_define_vencedora(self) -> None:
        """Melhor resultado deve aparecer como vencedor."""
        comparison = StrategyComparator().compare(
            [
                self._benchmark("alpha001", net_profit=100.0),
                self._benchmark("baseline", net_profit=50.0),
            ],
        )

        self.assertEqual(comparison.winning_strategy, "alpha001")
        self.assertEqual(comparison.ranking[0].strategy_name, "alpha001")

    def test_prioriza_status_approved(self) -> None:
        """Estrategia aprovada deve ficar acima de rejeitada."""
        comparison = StrategyComparator().compare(
            [
                self._entry("rejected", 200.0, "REJECTED"),
                self._entry("approved", 100.0, "APPROVED"),
            ],
        )

        self.assertEqual(comparison.ranking[0].strategy_name, "approved")

    def test_desempata_por_profit_factor(self) -> None:
        """Profit factor deve desempatar lucro igual."""
        comparison = StrategyComparator().compare(
            [
                self._benchmark("weak", net_profit=100.0, profit_factor=1.2),
                self._benchmark("strong", net_profit=100.0, profit_factor=2.0),
            ],
        )

        self.assertEqual(comparison.winning_strategy, "strong")

    def test_desempata_por_drawdown_menor(self) -> None:
        """Menor drawdown deve vencer quando metricas principais empatam."""
        comparison = StrategyComparator().compare(
            [
                self._benchmark("high_dd", net_profit=100.0, drawdown=30.0),
                self._benchmark("low_dd", net_profit=100.0, drawdown=10.0),
            ],
        )

        self.assertEqual(comparison.winning_strategy, "low_dd")

    def test_gera_diferencas_por_metrica(self) -> None:
        """Resultado deve incluir diferencas consolidadas."""
        comparison = StrategyComparator().compare(
            [
                self._benchmark("alpha001", net_profit=120.0),
                self._benchmark("baseline", net_profit=50.0),
            ],
        )

        differences = {
            item.metric_name: item.difference
            for item in comparison.metric_differences
        }
        self.assertEqual(differences["net_profit_points"], 70.0)
        self.assertIn("profit_factor", differences)

    def test_aceita_backtest_result_como_entrada(self) -> None:
        """BacktestResult deve ser reutilizado como contrato existente."""
        comparison = StrategyComparator().compare(
            [
                self._backtest(total_profit=80.0),
                self._backtest(total_profit=120.0),
            ],
        )

        self.assertEqual(comparison.winning_strategy, "strategy_2")
        self.assertEqual(comparison.ranking[0].net_profit_points, 120.0)

    def test_aceita_dict_com_backtest_result_nomeado(self) -> None:
        """Dicionario pode nomear a estrategia ao usar BacktestResult."""
        comparison = StrategyComparator().compare(
            [
                {
                    "strategy_name": "alpha001",
                    "backtest_result": self._backtest(total_profit=90.0),
                    "validation_status": "APPROVED",
                },
                {
                    "strategy_name": "alpha002",
                    "backtest_result": self._backtest(total_profit=70.0),
                    "validation_status": "APPROVED",
                },
            ],
        )

        self.assertEqual(comparison.winning_strategy, "alpha001")
        self.assertEqual(comparison.ranking[0].validation_status, "APPROVED")

    def test_aceita_dict_com_metricas(self) -> None:
        """Resultados simples em dict devem ser normalizados."""
        comparison = StrategyComparator().compare(
            [
                {
                    "strategy_name": "alpha001",
                    "total_trades": 20,
                    "win_rate": 0.6,
                    "profit_factor": 1.4,
                    "max_drawdown_points": 12.0,
                    "net_profit_points": 80.0,
                    "validation_status": "APPROVED",
                },
                {
                    "strategy_name": "alpha002",
                    "total_trades": 20,
                    "win_rate": 0.5,
                    "profit_factor": 1.2,
                    "max_drawdown_points": 20.0,
                    "net_profit_points": 60.0,
                    "validation_status": "APPROVED",
                },
            ],
        )

        self.assertEqual(comparison.ranking[0].strategy_name, "alpha001")

    def test_amostra_insuficiente_nao_quebra(self) -> None:
        """Menos de duas estrategias deve retornar resumo seguro."""
        comparison = StrategyComparator().compare(
            [self._benchmark("alpha001", net_profit=100.0)],
        )

        self.assertEqual(comparison.winning_strategy, "alpha001")
        self.assertEqual(comparison.metric_differences, [])
        self.assertIn("duas ou mais", comparison.summary)

    def test_retorna_strategy_comparison_result(self) -> None:
        """Comparator deve retornar DTO consolidado."""
        comparison = StrategyComparator().compare(
            [
                self._benchmark("alpha001", net_profit=100.0),
                self._benchmark("baseline", net_profit=50.0),
            ],
        )

        self.assertIsInstance(comparison, StrategyComparisonResult)
        self.assertIsInstance(comparison.ranking[0], StrategyComparisonEntry)
        self.assertIn("Estrategia vencedora", comparison.summary)

    def _benchmark(
        self,
        strategy_name: str,
        net_profit: float,
        profit_factor: float = 1.5,
        drawdown: float = 10.0,
    ) -> StrategyBenchmarkResult:
        return StrategyBenchmarkResult(
            strategy_name=strategy_name,
            total_trades=30,
            wins=18,
            losses=12,
            net_profit_points=net_profit,
            win_rate=0.6,
            profit_factor=profit_factor,
            max_drawdown_points=drawdown,
            equity_curve=[0.0, net_profit],
        )

    def _entry(
        self,
        strategy_name: str,
        net_profit: float,
        status: str,
    ) -> StrategyComparisonEntry:
        return StrategyComparisonEntry(
            strategy_name=strategy_name,
            total_trades=30,
            win_rate=0.6,
            profit_factor=1.5,
            max_drawdown_points=10.0,
            net_profit_points=net_profit,
            validation_status=status,
        )

    def _backtest(self, total_profit: float) -> BacktestResult:
        return BacktestResult(
            total_profit=total_profit,
            total_trades=30,
            win_rate=0.6,
            drawdown=10.0,
            profit_factor=1.5,
            sharpe=1.0,
        )


if __name__ == "__main__":
    unittest.main()
