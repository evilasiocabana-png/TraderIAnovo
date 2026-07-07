"""Testes do advisor estatistico do Research Lab."""

import unittest

from research.benchmark_comparator import BenchmarkComparison
from research.experiment_validator import ExperimentValidation
from research.research_advisor import (
    ResearchAdvisor,
    ResearchRecommendation,
)
from research.strategy_benchmark import StrategyBenchmarkResult


class ResearchAdvisorTest(unittest.TestCase):
    """Valida recomendacoes baseadas em benchmarks."""

    def test_sem_benchmark_nao_recomenda(self) -> None:
        """Garante ausencia de recomendacao sem benchmark."""
        recommendation = ResearchAdvisor().recommend(
            self._comparison([]),
            self._validation(),
        )

        self.assertIsInstance(recommendation, ResearchRecommendation)
        self.assertIsNone(recommendation.recommended_strategy)
        self.assertEqual(recommendation.confidence, 0.0)
        self.assertIsNone(recommendation.benchmark_used)
        self.assertIn("Nenhum benchmark disponivel", recommendation.warnings)

    def test_amostra_nao_relevante_nao_recomenda(self) -> None:
        """Garante bloqueio por pouca relevancia estatistica."""
        benchmark = self._benchmark("alpha", 100.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([benchmark]),
            self._validation(relevant=False, confidence_level="Nao confiavel"),
        )

        self.assertIsNone(recommendation.recommended_strategy)
        self.assertEqual(recommendation.confidence, 0.0)
        self.assertEqual(recommendation.benchmark_used, benchmark)
        self.assertIn(
            "Amostra estatisticamente insuficiente",
            recommendation.warnings,
        )

    def test_vencedor_claro_recomenda_estrategia(self) -> None:
        """Garante recomendacao quando ha vencedor claro."""
        best = self._benchmark("alpha", 100.0)
        second = self._benchmark("beta", 40.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([best, second]),
            self._validation(),
        )

        self.assertEqual(recommendation.recommended_strategy, "alpha")
        self.assertEqual(recommendation.benchmark_used, best)
        self.assertGreater(recommendation.confidence, 0.0)

    def test_empate_nao_recomenda(self) -> None:
        """Garante ausencia de recomendacao sem vencedor claro."""
        first = self._benchmark("alpha", 100.0)
        second = self._benchmark("beta", 100.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([first, second]),
            self._validation(),
        )

        self.assertIsNone(recommendation.recommended_strategy)
        self.assertIn(
            "Sem estrategia claramente superior",
            recommendation.warnings,
        )

    def test_confiabilidade_alta_gera_maior_confidence(self) -> None:
        """Garante confidence baseado na validacao."""
        benchmark = self._benchmark("alpha", 100.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([benchmark]),
            self._validation(confidence_level="Confiabilidade alta"),
        )

        self.assertEqual(recommendation.confidence, 85.0)

    def test_warnings_reduzem_confidence(self) -> None:
        """Garante penalizacao por alertas estatisticos."""
        benchmark = self._benchmark("alpha", 100.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([benchmark]),
            self._validation(warnings=["Profit Factor baixo"]),
        )

        self.assertEqual(recommendation.confidence, 60.0)
        self.assertIn("Profit Factor baixo", recommendation.warnings)

    def test_reason_explica_recomendacao(self) -> None:
        """Garante explicacao em linguagem simples."""
        benchmark = self._benchmark("alpha", 100.0)

        recommendation = ResearchAdvisor().recommend(
            self._comparison([benchmark]),
            self._validation(),
        )

        self.assertIn("alpha", recommendation.reason)
        self.assertIn("lucro liquido", recommendation.reason)

    def _comparison(
        self,
        ranking: list[StrategyBenchmarkResult],
    ) -> BenchmarkComparison:
        best = ranking[0] if ranking else None
        return BenchmarkComparison(
            best_strategy=best.strategy_name if best else None,
            best_profit=best.net_profit_points if best else 0.0,
            best_profit_factor=best.profit_factor if best else 0.0,
            best_drawdown=best.max_drawdown_points if best else 0.0,
            best_win_rate=best.win_rate if best else 0.0,
            ranking=ranking,
        )

    def _validation(
        self,
        relevant: bool = True,
        confidence_level: str = "Confiabilidade media",
        warnings: list[str] | None = None,
    ) -> ExperimentValidation:
        return ExperimentValidation(
            sample_size=50 if relevant else 10,
            is_statistically_relevant=relevant,
            confidence_level=confidence_level,
            warnings=[] if warnings is None else warnings,
            summary="Validacao estatistica de teste.",
        )

    def _benchmark(
        self,
        strategy_name: str,
        net_profit_points: float,
    ) -> StrategyBenchmarkResult:
        return StrategyBenchmarkResult(
            strategy_name=strategy_name,
            total_trades=50,
            wins=30,
            losses=20,
            net_profit_points=net_profit_points,
            win_rate=0.60,
            profit_factor=1.5,
            max_drawdown_points=20.0,
            equity_curve=[0.0, net_profit_points],
        )


if __name__ == "__main__":
    unittest.main()
