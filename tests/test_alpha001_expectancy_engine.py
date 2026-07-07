"""Testes do motor de Expectancy da Alpha 001."""

import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_expectancy_engine import (
    Alpha001ExpectancyEngine,
    Alpha001ExpectancyResult,
)
from research.alpha001_experiment import Alpha001ExperimentResult


class Alpha001ExpectancyEngineTest(unittest.TestCase):
    """Valida calculo isolado de Expectancy."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001ExpectancyEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001ExpectancyResult)

    def test_calculate_retorna_campos_de_expectancy(self) -> None:
        result = Alpha001ExpectancyEngine().calculate(self._experiment_result())

        self.assertEqual(result.average_win, 0.0)
        self.assertEqual(result.average_loss, 0.0)
        self.assertEqual(result.payoff_ratio, 0.0)
        self.assertEqual(result.expectancy, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        result = Alpha001ExpectancyEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "sharpe",
            "sortino",
            "calmar",
            "drawdown",
            "max_drawdown_points",
            "profit_factor",
            "win_rate",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open(
            "research/alpha001_expectancy_engine.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Alpha001Config",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
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
