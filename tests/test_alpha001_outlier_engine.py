"""Testes do motor de outliers da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_outlier_engine import (
    Alpha001OutlierEngine,
    Alpha001OutlierResult,
)
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001OutlierEngineTest(unittest.TestCase):
    """Valida deteccao de dependencia de operacoes extremas."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001OutlierResult))
        self.assertTrue(Alpha001OutlierResult.__dataclass_params__.frozen)

    def test_calcula_maiores_operacoes_e_contribuicao(self) -> None:
        result = Alpha001OutlierEngine().calculate(
            self._research_result(
                average_win=40.0,
                average_loss=20.0,
                gross_profit=160.0,
                gross_loss=40.0,
            ),
        )

        self.assertEqual(result.largest_winning_trade, 40.0)
        self.assertEqual(result.largest_losing_trade, 20.0)
        self.assertEqual(result.largest_trade_contribution_percent, 20.0)
        self.assertFalse(result.outlier_detected)

    def test_detecta_outlier_por_contribuicao_excessiva(self) -> None:
        result = Alpha001OutlierEngine(
            contribution_threshold_percent=50.0,
        ).calculate(
            self._research_result(
                average_win=80.0,
                average_loss=10.0,
                gross_profit=100.0,
                gross_loss=20.0,
            ),
        )

        self.assertGreaterEqual(result.largest_trade_contribution_percent, 50.0)
        self.assertTrue(result.outlier_detected)

    def test_sem_movimento_financeiro_retorna_zero_sem_outlier(self) -> None:
        result = Alpha001OutlierEngine().calculate(
            self._research_result(
                average_win=0.0,
                average_loss=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
            ),
        )

        self.assertEqual(result.largest_winning_trade, 0.0)
        self.assertEqual(result.largest_losing_trade, 0.0)
        self.assertEqual(result.largest_trade_contribution_percent, 0.0)
        self.assertFalse(result.outlier_detected)

    def test_sem_trades_vencedores_ou_perdedores_retorna_zero(self) -> None:
        result = Alpha001OutlierEngine().calculate(
            self._research_result(
                winning_trades=0,
                losing_trades=0,
                average_win=50.0,
                average_loss=30.0,
            ),
        )

        self.assertEqual(result.largest_winning_trade, 0.0)
        self.assertEqual(result.largest_losing_trade, 0.0)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001OutlierEngine().calculate(self._research_result())

        with self.assertRaises(FrozenInstanceError):
            result.outlier_detected = True

    def test_engine_nao_calcula_metricas_fora_do_escopo(self) -> None:
        source = read_source(Path("research/alpha001_outlier_engine.py"))
        forbidden_fragments = (
            "sharpe",
            "sortino",
            "Alpha001DrawdownEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001WinRateEngine",
            "Alpha001ExpectancyEngine",
            "Alpha001ProfitEngine",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_outlier_engine.py")
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

    def test_engine_nao_altera_resultados_financeiros_existentes(self) -> None:
        source = read_source(Path("research/alpha001_outlier_engine.py"))

        self.assertIn("Alpha001ResearchResult", source)
        self.assertNotIn("Alpha001ResearchResult(", source)
        self.assertNotIn("Alpha001ProfitResult(", source)
        self.assertNotIn(".calculate(", source)

    def _research_result(
        self,
        *,
        winning_trades: int = 4,
        losing_trades: int = 2,
        average_win: float = 40.0,
        average_loss: float = 20.0,
        gross_profit: float = 160.0,
        gross_loss: float = 40.0,
    ) -> Alpha001ResearchResult:
        total_trades = winning_trades + losing_trades
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=total_trades,
                total_buy=total_trades,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=gross_profit,
                gross_loss_points=gross_loss,
                net_profit_points=gross_profit - abs(gross_loss),
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0,),
                max_drawdown_points=0.0,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                breakeven_trades=0,
                win_rate=0.0,
            ),
            profit_factor=Alpha001ProfitFactorResult(profit_factor=0.0),
            expectancy=Alpha001ExpectancyResult(
                average_win=average_win,
                average_loss=average_loss,
                payoff_ratio=0.0,
                expectancy=0.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
