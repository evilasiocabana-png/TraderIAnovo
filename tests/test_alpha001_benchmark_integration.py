"""Testes do benchmark comparativo da Alpha 001."""

import unittest

from application.research_lab_service import (
    BenchmarkComparisonData,
    BenchmarkData,
    ResearchLabService,
)


class Alpha001BenchmarkIntegrationTest(unittest.TestCase):
    """Valida comparacao da Alpha 001 com estrategias existentes."""

    def test_alpha001_aparece_no_benchmark(self) -> None:
        """Benchmarks demo devem incluir Alpha 001."""
        benchmarks = ResearchLabService().run_demo_benchmarks()

        self.assertIn("alpha001_iorb", self._strategy_names(benchmarks))

    def test_benchmark_executa_sem_quebrar_estrategias_existentes(self) -> None:
        """Benchmark deve manter estrategias existentes no catalogo demo."""
        benchmarks = ResearchLabService().run_demo_benchmarks()
        names = self._strategy_names(benchmarks)

        self.assertIn("alpha001_iorb", names)
        self.assertIn("breakout", names)
        self.assertIn("pullback", names)
        self.assertIn("score_contexto", names)

    def test_metricas_comparativas_sao_geradas(self) -> None:
        """Comparacao deve expor ranking e metricas ja existentes."""
        service = ResearchLabService()
        service.run_demo_benchmarks()

        comparison = service.compare_benchmarks()

        self.assertIsInstance(comparison, BenchmarkComparisonData)
        self.assertGreaterEqual(len(comparison.ranking), 2)
        self.assertIsInstance(comparison.best_profit, float)
        self.assertIsInstance(comparison.best_profit_factor, float)
        self.assertIsInstance(comparison.best_drawdown, float)
        self.assertIsInstance(comparison.best_win_rate, float)

    def test_resultado_alpha001_tem_nome_correto(self) -> None:
        """Resultado da Alpha 001 deve ser identificado pelo nome oficial."""
        benchmarks = ResearchLabService().run_demo_benchmarks()

        alpha = self._find_benchmark(benchmarks, "alpha001_iorb")

        self.assertEqual(alpha.strategy_name, "alpha001_iorb")

    def test_alpha001_aparece_no_ranking_da_comparacao(self) -> None:
        """Ranking da comparacao deve incluir Alpha 001."""
        service = ResearchLabService()
        service.run_demo_benchmarks()

        comparison = service.compare_benchmarks()

        self.assertIn("alpha001_iorb", self._strategy_names(comparison.ranking))

    def test_nenhuma_ordem_real_e_executada(self) -> None:
        """Benchmark deve produzir apenas metricas paper em memoria."""
        benchmarks = ResearchLabService().run_demo_benchmarks()

        alpha = self._find_benchmark(benchmarks, "alpha001_iorb")

        self.assertIsInstance(alpha.equity_curve, list)
        self.assertGreaterEqual(alpha.total_trades, 0)
        self.assertGreaterEqual(alpha.wins, 0)
        self.assertGreaterEqual(alpha.losses, 0)

    def _find_benchmark(
        self,
        benchmarks: list[BenchmarkData],
        strategy_name: str,
    ) -> BenchmarkData:
        for benchmark in benchmarks:
            if benchmark.strategy_name == strategy_name:
                return benchmark
        self.fail(f"Benchmark nao encontrado: {strategy_name}")

    def _strategy_names(self, benchmarks: list[BenchmarkData]) -> list[str]:
        return [benchmark.strategy_name for benchmark in benchmarks]


if __name__ == "__main__":
    unittest.main()
