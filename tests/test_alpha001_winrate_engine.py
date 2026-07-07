"""Testes do motor de taxa de acerto da Alpha 001."""

import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_winrate_engine import (
    Alpha001WinRateEngine,
    Alpha001WinRateResult,
)


class Alpha001WinRateEngineTest(unittest.TestCase):
    """Valida calculo de taxa de acerto isolado da Alpha001."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001WinRateResult)

    def test_calculate_retorna_campos_de_winrate(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        self.assertEqual(result.winning_trades, 0)
        self.assertEqual(result.losing_trades, 0)
        self.assertEqual(result.breakeven_trades, 0)
        self.assertEqual(result.win_rate, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "profit_factor",
            "expectancy",
            "sharpe",
            "drawdown",
            "max_drawdown_points",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open("research/alpha001_winrate_engine.py", encoding="utf-8") as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Alpha001Config",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Broker",
            "MT5",
            "database",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _experiment_result(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=3,
            total_signals=3,
            total_buy=1,
            total_sell=1,
            total_wait=1,
            execution_time_ms=1.0,
            signals=(
                StrategySignal("BUY", 100, 1.0, []),
                StrategySignal("SELL", 100, 1.0, []),
                StrategySignal("WAIT", 0, 0.0, []),
            ),
        )


if __name__ == "__main__":
    unittest.main()
