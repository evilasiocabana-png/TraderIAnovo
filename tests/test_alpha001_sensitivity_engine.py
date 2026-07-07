"""Testes do motor de sensibilidade parametrica da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_sensitivity_engine import (
    Alpha001SensitivityEngine,
    Alpha001SensitivityResult,
)
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001SensitivityEngineTest(unittest.TestCase):
    """Valida analise de sensibilidade sem otimizacao parametrica."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001SensitivityResult))
        self.assertTrue(Alpha001SensitivityResult.__dataclass_params__.frozen)

    def test_calcula_variacoes_das_metricas_existentes(self) -> None:
        result = Alpha001SensitivityEngine().calculate(
            [
                self._research_result(
                    net_profit=100.0,
                    drawdown=20.0,
                    profit_factor=1.4,
                    win_rate=0.48,
                ),
                self._research_result(
                    net_profit=175.0,
                    drawdown=35.0,
                    profit_factor=2.1,
                    win_rate=0.61,
                ),
                self._research_result(
                    net_profit=130.0,
                    drawdown=28.0,
                    profit_factor=1.8,
                    win_rate=0.55,
                ),
            ],
        )

        self.assertEqual(result.variation_of_net_profit, 75.0)
        self.assertEqual(result.variation_of_drawdown, 15.0)
        self.assertAlmostEqual(result.variation_of_profit_factor, 0.7)
        self.assertAlmostEqual(result.variation_of_win_rate, 0.13)

    def test_colecao_vazia_retorna_variacoes_zero(self) -> None:
        result = Alpha001SensitivityEngine().calculate([])

        self.assertEqual(result.variation_of_net_profit, 0.0)
        self.assertEqual(result.variation_of_drawdown, 0.0)
        self.assertEqual(result.variation_of_profit_factor, 0.0)
        self.assertEqual(result.variation_of_win_rate, 0.0)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001SensitivityEngine().calculate([])

        with self.assertRaises(FrozenInstanceError):
            result.variation_of_net_profit = 1.0

    def test_engine_nao_otimiza_parametros_nem_usa_ia(self) -> None:
        source = read_source(Path("research/alpha001_sensitivity_engine.py"))
        forbidden_fragments = (
            "optimize",
            "optimizer",
            "best_parameters",
            "genetic",
            "machine_learning",
            "openai",
            "Alpha001Experiment",
            "run_experiment",
            "run_alpha001",
            "with_overrides",
            "Alpha001Config(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_sensitivity_engine.py")
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
        net_profit: float,
        drawdown: float,
        profit_factor: float,
        win_rate: float,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=30,
                total_buy=30,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=max(net_profit, 0.0),
                gross_loss_points=0.0,
                net_profit_points=net_profit,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0,),
                max_drawdown_points=drawdown,
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
                expectancy=0.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
