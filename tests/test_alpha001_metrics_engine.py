"""Testes do motor de metricas estruturais da Alpha 001."""

import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import (
    Alpha001MetricsEngine,
    Alpha001MetricsResult,
)


class Alpha001MetricsEngineTest(unittest.TestCase):
    """Valida calculo de metricas estruturais da Alpha001."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001MetricsEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001MetricsResult)

    def test_calcula_total_trades_com_buy_e_sell(self) -> None:
        result = Alpha001MetricsEngine().calculate(
            self._experiment_result(total_buy=2, total_sell=3, total_wait=4)
        )

        self.assertEqual(result.total_trades, 5)
        self.assertEqual(result.total_buy, 2)
        self.assertEqual(result.total_sell, 3)
        self.assertEqual(result.total_wait, 4)

    def test_aceita_experimento_sem_sinais(self) -> None:
        result = Alpha001MetricsEngine().calculate(
            self._experiment_result(total_buy=0, total_sell=0, total_wait=0)
        )

        self.assertEqual(result.total_trades, 0)
        self.assertEqual(result.total_buy, 0)
        self.assertEqual(result.total_sell, 0)
        self.assertEqual(result.total_wait, 0)

    def test_nao_calcula_metricas_financeiras(self) -> None:
        result = Alpha001MetricsEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "profit",
            "net_profit",
            "gross_profit",
            "drawdown",
            "profit_factor",
            "win_rate",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open("research/alpha001_metrics_engine.py", encoding="utf-8") as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "Broker",
            "Alpha001Config",
            "StrategySignal(",
            "database",
            "sqlite",
            "mt5",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _experiment_result(
        self,
        total_buy: int = 1,
        total_sell: int = 1,
        total_wait: int = 1,
    ) -> Alpha001ExperimentResult:
        signals = (
            StrategySignal("BUY", 100, 1.0, []),
            StrategySignal("SELL", 100, 1.0, []),
            StrategySignal("WAIT", 0, 0.0, []),
        )
        return Alpha001ExperimentResult(
            total_candles=total_buy + total_sell + total_wait,
            total_signals=total_buy + total_sell + total_wait,
            total_buy=total_buy,
            total_sell=total_sell,
            total_wait=total_wait,
            execution_time_ms=1.0,
            signals=signals,
        )


if __name__ == "__main__":
    unittest.main()
