"""Testes do motor de significancia estatistica da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_statistical_significance_engine import (
    Alpha001StatisticalSignificanceEngine,
    Alpha001StatisticalSignificanceResult,
)
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001StatisticalSignificanceEngineTest(unittest.TestCase):
    """Valida indicadores estatisticos derivados do resultado de pesquisa."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001StatisticalSignificanceResult))
        self.assertTrue(
            Alpha001StatisticalSignificanceResult.__dataclass_params__.frozen
        )

    def test_calcula_indicadores_estatisticos(self) -> None:
        result = Alpha001StatisticalSignificanceEngine().calculate(
            self._research_result(
                winning_trades=2,
                losing_trades=1,
                breakeven_trades=1,
                average_win=10.0,
                average_loss=5.0,
            ),
        )

        self.assertEqual(result.mean_return, 3.75)
        self.assertAlmostEqual(result.standard_deviation, 7.5)
        self.assertAlmostEqual(result.standard_error, 3.75)
        self.assertAlmostEqual(result.t_score, 1.0)
        self.assertFalse(result.significance_flag)

    def test_marca_significancia_quando_t_score_supera_limite(self) -> None:
        result = Alpha001StatisticalSignificanceEngine().calculate(
            self._research_result(
                winning_trades=4,
                losing_trades=1,
                breakeven_trades=0,
                average_win=12.0,
                average_loss=1.0,
            ),
        )

        self.assertGreaterEqual(result.t_score, 2.0)
        self.assertTrue(result.significance_flag)

    def test_sem_operacoes_retorna_indicadores_zero(self) -> None:
        result = Alpha001StatisticalSignificanceEngine().calculate(
            self._research_result(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                average_win=0.0,
                average_loss=0.0,
            ),
        )

        self.assertEqual(result.mean_return, 0.0)
        self.assertEqual(result.standard_deviation, 0.0)
        self.assertEqual(result.standard_error, 0.0)
        self.assertEqual(result.t_score, 0.0)
        self.assertFalse(result.significance_flag)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001StatisticalSignificanceEngine().calculate(
            self._research_result(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                average_win=0.0,
                average_loss=0.0,
            ),
        )

        with self.assertRaises(FrozenInstanceError):
            result.mean_return = 1.0

    def test_engine_nao_implementa_tecnicas_fora_do_escopo(self) -> None:
        source = read_source(
            Path("research/alpha001_statistical_significance_engine.py")
        )
        forbidden_fragments = (
            "bootstrap",
            "bayesian",
            "machine learning",
            "machine_learning",
            "openai",
            "sklearn",
            "tensorflow",
            "torch",
            "optimize",
            "optimizer",
            "best_parameters",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_statistical_significance_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
            "alpha",
            "strategies",
        }
        forbidden_calls = {
            "open",
            "write",
            "run",
            "generate_signal",
            "order_send",
            "execute_order",
            "next_candle",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _research_result(
        self,
        *,
        winning_trades: int,
        losing_trades: int,
        breakeven_trades: int,
        average_win: float,
        average_loss: float,
    ) -> Alpha001ResearchResult:
        net_profit = (
            winning_trades * average_win
            - losing_trades * abs(average_loss)
        )
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=winning_trades + losing_trades,
                total_buy=winning_trades + losing_trades,
                total_sell=0,
                total_wait=breakeven_trades,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=winning_trades * average_win,
                gross_loss_points=losing_trades * abs(average_loss),
                net_profit_points=net_profit,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0,),
                max_drawdown_points=0.0,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                breakeven_trades=breakeven_trades,
                win_rate=0.0,
            ),
            profit_factor=Alpha001ProfitFactorResult(
                profit_factor=0.0,
            ),
            expectancy=Alpha001ExpectancyResult(
                average_win=average_win,
                average_loss=average_loss,
                payoff_ratio=0.0,
                expectancy=0.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
