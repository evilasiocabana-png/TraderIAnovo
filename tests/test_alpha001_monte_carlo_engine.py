"""Testes do motor Monte Carlo da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_monte_carlo_engine import (
    Alpha001MonteCarloEngine,
    Alpha001MonteCarloResult,
)
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001MonteCarloEngineTest(unittest.TestCase):
    """Valida simulacao Monte Carlo sobre Alpha001ResearchResult."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001MonteCarloResult))
        self.assertTrue(Alpha001MonteCarloResult.__dataclass_params__.frozen)

    def test_calcula_estatisticas_monte_carlo(self) -> None:
        result = Alpha001MonteCarloEngine(
            total_simulations=20,
            seed=42,
        ).calculate(self._research_result())

        self.assertEqual(result.total_simulations, 20)
        self.assertEqual(result.average_net_profit, 100.0)
        self.assertEqual(result.median_net_profit, 100.0)
        self.assertEqual(result.worst_simulation, 100.0)
        self.assertEqual(result.best_simulation, 100.0)
        self.assertGreaterEqual(result.average_drawdown, 0.0)

    def test_seed_igual_produz_resultado_deterministico(self) -> None:
        first = Alpha001MonteCarloEngine(
            total_simulations=50,
            seed=7,
        ).calculate(self._research_result())
        second = Alpha001MonteCarloEngine(
            total_simulations=50,
            seed=7,
        ).calculate(self._research_result())

        self.assertEqual(first, second)

    def test_sem_operacoes_retorna_resultado_zero(self) -> None:
        result = Alpha001MonteCarloEngine(
            total_simulations=20,
            seed=1,
        ).calculate(
            self._research_result(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
            ),
        )

        self.assertEqual(result.total_simulations, 0)
        self.assertEqual(result.average_net_profit, 0.0)
        self.assertEqual(result.average_drawdown, 0.0)

    def test_simulacoes_zero_retorna_resultado_zero(self) -> None:
        result = Alpha001MonteCarloEngine(
            total_simulations=0,
            seed=1,
        ).calculate(self._research_result())

        self.assertEqual(result.total_simulations, 0)
        self.assertEqual(result.worst_simulation, 0.0)

    def test_nao_modifica_resultado_original(self) -> None:
        research_result = self._research_result()
        original = research_result.win_rate

        Alpha001MonteCarloEngine(total_simulations=20, seed=2).calculate(
            research_result,
        )

        self.assertIs(research_result.win_rate, original)
        self.assertEqual(research_result.win_rate.winning_trades, 3)
        self.assertEqual(research_result.win_rate.losing_trades, 2)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001MonteCarloEngine(
            total_simulations=1,
            seed=1,
        ).calculate(self._research_result())

        with self.assertRaises(FrozenInstanceError):
            result.total_simulations = 2

    def test_engine_nao_implementa_dashboard_exportacao_ia_ou_graficos(self) -> None:
        source = read_source(Path("research/alpha001_monte_carlo_engine.py"))
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "export",
            "csv",
            "chart",
            "plot",
            "openai",
            "machine_learning",
            "sklearn",
            "IA",
            "AI",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_monte_carlo_engine.py")
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
        winning_trades: int = 3,
        losing_trades: int = 2,
        breakeven_trades: int = 1,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=winning_trades + losing_trades,
                total_buy=winning_trades + losing_trades,
                total_sell=0,
                total_wait=breakeven_trades,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=150.0,
                gross_loss_points=50.0,
                net_profit_points=100.0,
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
                win_rate=0.6,
            ),
            profit_factor=Alpha001ProfitFactorResult(profit_factor=3.0),
            expectancy=Alpha001ExpectancyResult(
                average_win=50.0,
                average_loss=25.0,
                payoff_ratio=2.0,
                expectancy=20.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
