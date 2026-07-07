"""Testes do motor de drawdown da Alpha 001."""

import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_drawdown_engine import (
    Alpha001DrawdownEngine,
    Alpha001DrawdownResult,
)
from research.alpha001_experiment import Alpha001ExperimentResult


class Alpha001DrawdownEngineTest(unittest.TestCase):
    """Valida calculo de drawdown isolado da Alpha001."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001DrawdownEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001DrawdownResult)

    def test_calculate_retorna_campos_de_drawdown(self) -> None:
        result = Alpha001DrawdownEngine().calculate(self._experiment_result())

        self.assertEqual(result.equity_curve, (0.0,))
        self.assertEqual(result.max_drawdown_points, 0.0)
        self.assertEqual(result.max_drawdown_percent, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        result = Alpha001DrawdownEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "profit_factor",
            "win_rate",
            "expectancy",
            "sharpe",
            "sortino",
            "recovery_factor",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open("research/alpha001_drawdown_engine.py", encoding="utf-8") as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Alpha001Config",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
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
