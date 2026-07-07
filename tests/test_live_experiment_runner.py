"""Testes do experimento live em memoria."""

import inspect
import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.live_experiment_runner import LiveExperimentRunner


class LiveExperimentRunnerTest(unittest.TestCase):
    def test_runner_registra_sinais_e_calcula_estatisticas(self) -> None:
        runner = LiveExperimentRunner()

        runner.record_signal(
            StrategySignal("BUY", score=10, confidence=0.80),
            timestamp="2026-06-29T01:00:00+00:00",
            symbol="EURUSD",
            timeframe="H1",
            strategy_name="alpha_a",
            regime="TREND",
        )
        runner.record_signal(
            StrategySignal("WAIT", score=0, confidence=0.40),
            timestamp="2026-06-29T02:00:00+00:00",
            symbol="EURUSD",
            timeframe="H1",
            strategy_name="alpha_b",
            regime="RANGE",
        )
        runner.record_signal(
            StrategySignal("SELL", score=-10, confidence=0.60),
            timestamp="2026-06-29T03:00:00+00:00",
            symbol="EURUSD",
            timeframe="H1",
            strategy_name="alpha_a",
            regime="TREND",
        )

        summary = runner.summary()

        self.assertEqual(summary.total_signals, 3)
        self.assertEqual(summary.buy_count, 1)
        self.assertEqual(summary.sell_count, 1)
        self.assertEqual(summary.wait_count, 1)
        self.assertAlmostEqual(summary.average_confidence, 0.60)
        self.assertAlmostEqual(summary.confidence_std, 0.16329931618554522)
        self.assertEqual(summary.by_regime, {"TREND": 2, "RANGE": 1})
        self.assertEqual(summary.by_strategy, {"alpha_a": 2, "alpha_b": 1})

    def test_runner_nao_contem_capacidade_operacional(self) -> None:
        source = inspect.getsource(LiveExperimentRunner)
        forbidden_fragments = {
            "order" + "_send",
            "orders" + "_get",
            "positions" + "_get",
            "positions" + "_total",
            "Broker",
        }

        self.assertEqual(
            [item for item in forbidden_fragments if item in source],
            [],
        )


if __name__ == "__main__":
    unittest.main()
