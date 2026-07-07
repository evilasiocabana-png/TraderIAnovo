"""Testes do motor de resultado financeiro basico da Alpha 001."""

import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_profit_engine import (
    Alpha001ProfitEngine,
    Alpha001ProfitResult,
)


class Alpha001ProfitEngineTest(unittest.TestCase):
    """Valida calculo financeiro basico isolado da Alpha001."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001ProfitEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001ProfitResult)

    def test_calculate_retorna_campos_financeiros_basicos(self) -> None:
        result = Alpha001ProfitEngine().calculate(self._experiment_result())

        self.assertEqual(result.gross_profit_points, 0.0)
        self.assertEqual(result.gross_loss_points, 0.0)
        self.assertEqual(result.net_profit_points, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        result = Alpha001ProfitEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "profit_factor",
            "win_rate",
            "drawdown",
            "expectancy",
            "sharpe",
            "sortino",
            "calmar",
            "recovery_factor",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open("research/alpha001_profit_engine.py", encoding="utf-8") as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Alpha001Config",
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
