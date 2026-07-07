"""Testes do agregador de resultados de pesquisa da Alpha 001."""

import unittest
from dataclasses import FrozenInstanceError

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult


class Alpha001ResearchReportContractTest(unittest.TestCase):
    """Valida agregacao pura dos resultados Alpha 001."""

    def test_cria_resultado_consolidado_tipado(self) -> None:
        result = self._research_result()

        self.assertIsInstance(result.metrics, Alpha001MetricsResult)
        self.assertIsInstance(result.profit, Alpha001ProfitResult)
        self.assertIsInstance(result.drawdown, Alpha001DrawdownResult)
        self.assertIsInstance(result.win_rate, Alpha001WinRateResult)
        self.assertIsInstance(result.profit_factor, Alpha001ProfitFactorResult)
        self.assertIsInstance(result.expectancy, Alpha001ExpectancyResult)

    def test_preserva_os_resultados_recebidos_sem_recalcular(self) -> None:
        metrics = Alpha001MetricsResult(
            total_trades=3,
            total_buy=1,
            total_sell=2,
            total_wait=4,
        )
        profit = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=40.0,
            net_profit_points=80.0,
        )
        drawdown = Alpha001DrawdownResult(
            equity_curve=(0.0, 80.0),
            max_drawdown_points=10.0,
            max_drawdown_percent=5.0,
        )
        win_rate = Alpha001WinRateResult(
            winning_trades=2,
            losing_trades=1,
            breakeven_trades=0,
            win_rate=0.66,
        )
        profit_factor = Alpha001ProfitFactorResult(profit_factor=3.0)
        expectancy = Alpha001ExpectancyResult(
            average_win=60.0,
            average_loss=40.0,
            payoff_ratio=1.5,
            expectancy=20.0,
        )

        result = Alpha001ResearchResult(
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )

        self.assertIs(result.metrics, metrics)
        self.assertIs(result.profit, profit)
        self.assertIs(result.drawdown, drawdown)
        self.assertIs(result.win_rate, win_rate)
        self.assertIs(result.profit_factor, profit_factor)
        self.assertIs(result.expectancy, expectancy)

    def test_resultado_e_imutavel(self) -> None:
        result = self._research_result()

        with self.assertRaises(FrozenInstanceError):
            result.metrics = Alpha001MetricsResult(0, 0, 0, 0)

    def test_nao_expoe_campos_fora_do_escopo(self) -> None:
        result = self._research_result()

        forbidden_fields = (
            "summary",
            "conclusion",
            "chart",
            "dashboard",
            "persisted_at",
            "generated_file",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_engines_ou_camadas_operacionais(self) -> None:
        with open(
            "research/alpha001_research_report.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "Replay",
            "Dashboard",
            "domain",
            "DecisionPipeline",
            "EventBus",
            "Broker",
            "MT5",
            "open(",
            "write",
            ".calculate(",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _research_result(self) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=1,
                total_buy=1,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=0.0,
                gross_loss_points=0.0,
                net_profit_points=0.0,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0,),
                max_drawdown_points=0.0,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate=0.0,
            ),
            profit_factor=Alpha001ProfitFactorResult(profit_factor=0.0),
            expectancy=Alpha001ExpectancyResult(
                average_win=0.0,
                average_loss=0.0,
                payoff_ratio=0.0,
                expectancy=0.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
