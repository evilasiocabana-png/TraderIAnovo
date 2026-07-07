"""Testes do resumo estatistico da varredura Alpha 001."""

import unittest

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)
from research.alpha001_research_summary import (
    Alpha001ResearchSummary,
    Alpha001ResearchSummaryResult,
)


class Alpha001ResearchSummaryTest(unittest.TestCase):
    """Valida agregacao estatistica de resultados existentes."""

    def test_total_de_experimentos(self) -> None:
        """Resumo deve contar todos os resultados recebidos."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertEqual(summary.total_experiments, 3)

    def test_total_aprovados_e_rejeitados(self) -> None:
        """Resumo deve separar aprovados e rejeitados."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertEqual(summary.total_approved, 2)
        self.assertEqual(summary.total_rejected, 1)

    def test_melhor_profit_factor(self) -> None:
        """Resumo deve expor maior profit factor."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertEqual(summary.best_profit_factor, 2.5)

    def test_menor_drawdown(self) -> None:
        """Resumo deve expor menor max drawdown."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertEqual(summary.lowest_max_drawdown_points, 5.0)

    def test_melhor_net_profit_points(self) -> None:
        """Resumo deve expor melhor lucro liquido."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertEqual(summary.best_net_profit_points, 150.0)

    def test_melhor_configuracao(self) -> None:
        """Melhor configuracao deve acompanhar melhor net profit."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertIsNotNone(summary.best_configuration)
        self.assertEqual(summary.best_configuration.opening_range_minutes, 10)

    def test_taxa_de_aprovacao(self) -> None:
        """Resumo deve calcular taxa de aprovacao."""
        summary = Alpha001ResearchSummary().summarize(self._results())

        self.assertAlmostEqual(summary.approval_rate, 2 / 3)

    def test_lista_vazia(self) -> None:
        """Resumo vazio deve retornar valores neutros."""
        summary = Alpha001ResearchSummary().summarize([])

        self.assertIsInstance(summary, Alpha001ResearchSummaryResult)
        self.assertEqual(summary.total_experiments, 0)
        self.assertIsNone(summary.best_configuration)
        self.assertEqual(summary.approval_rate, 0.0)

    def test_nao_altera_resultados_originais(self) -> None:
        """Summarizer nao deve ordenar ou alterar a lista recebida."""
        results = self._results()
        original = list(results)

        Alpha001ResearchSummary().summarize(results)

        self.assertEqual(results, original)

    def _results(self) -> list[Alpha001ParameterSweepResult]:
        return [
            self._result(5, "APPROVED", 1.5, 10.0, 100.0),
            self._result(10, "APPROVED", 2.5, 20.0, 150.0),
            self._result(15, "LOW_PROFIT_FACTOR", 0.8, 5.0, -20.0),
        ]

    def _result(
        self,
        opening_range: int,
        status: str,
        profit_factor: float,
        drawdown: float,
        net_profit: float,
    ) -> Alpha001ParameterSweepResult:
        return Alpha001ParameterSweepResult(
            parameters=Alpha001ParameterSet(opening_range, 20.0, 1000),
            total_trades=10,
            win_rate=0.6,
            profit_factor=profit_factor,
            max_drawdown_points=drawdown,
            net_profit_points=net_profit,
            validation_status=status,
        )


if __name__ == "__main__":
    unittest.main()
