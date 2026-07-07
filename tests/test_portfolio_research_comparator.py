"""Testes do comparador de pesquisas de portfolio."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.portfolio.portfolio_research_comparator import (
    PortfolioComparisonResult,
    PortfolioResearchComparator,
    PortfolioResearchComparison,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioResearchComparatorTest(unittest.TestCase):
    """Valida comparacao consolidada entre Alphas."""

    def test_resultados_sao_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioResearchComparison))
        self.assertTrue(PortfolioResearchComparison.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(PortfolioComparisonResult))
        self.assertTrue(PortfolioComparisonResult.__dataclass_params__.frozen)

    def test_compare_consolida_metricas_existentes(self) -> None:
        result = PortfolioResearchComparator().compare(
            [
                self._research_result(
                    total_trades=10,
                    net_profit=50.0,
                    max_drawdown=5.0,
                    profit_factor=1.5,
                    expectancy=3.0,
                    win_rate=0.6,
                ),
            ],
        )

        self.assertEqual(result.total_results, 1)
        comparison = result.comparisons[0]
        self.assertEqual(comparison.alpha_id, "Alpha001")
        self.assertEqual(comparison.total_trades, 10)
        self.assertEqual(comparison.net_profit, 50.0)
        self.assertEqual(comparison.max_drawdown, 5.0)
        self.assertEqual(comparison.profit_factor, 1.5)
        self.assertEqual(comparison.expectancy, 3.0)
        self.assertEqual(comparison.win_rate, 0.6)

    def test_compare_preserva_ordem_recebida_sem_ranking(self) -> None:
        weak = self._research_result(net_profit=10.0)
        strong = self._research_result(net_profit=100.0)

        result = PortfolioResearchComparator().compare([weak, strong])

        self.assertEqual(result.comparisons[0].net_profit, 10.0)
        self.assertEqual(result.comparisons[1].net_profit, 100.0)

    def test_compare_retorna_resultado_vazio(self) -> None:
        result = PortfolioResearchComparator().compare([])

        self.assertEqual(result.total_results, 0)
        self.assertEqual(result.comparisons, ())

    def test_comparison_e_imutavel(self) -> None:
        result = PortfolioResearchComparator().compare([self._research_result()])

        with self.assertRaises(FrozenInstanceError):
            result.comparisons[0].net_profit = 1.0

    def test_comparator_nao_calcula_metricas_novas_ou_ranking(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_research_comparator.py")
        )
        forbidden_fragments = (
            "sorted(",
            "ranking",
            "best_",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
            ".calculate(",
            ".run(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_comparator_nao_gera_graficos_dashboard_ou_persistencia(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_research_comparator.py")
        )
        forbidden_fragments = (
            "matplotlib",
            "plot",
            "dashboard",
            "streamlit",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_comparator_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_research_comparator.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

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
