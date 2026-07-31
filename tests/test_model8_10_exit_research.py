from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from research.alpha_suggested.model8_10_exit_research import (
    TradeResult,
    _ranking_key,
    calculate_metrics,
    replay_trades,
)


class Model8To10ExitResearchTest(unittest.TestCase):
    def test_same_candle_collision_is_conservative_stop(self) -> None:
        index = pd.date_range("2026-01-01", periods=4, freq="5min", tz="UTC")
        candles = pd.DataFrame(
            {
                "open": [1.0, 1.0, 1.0, 1.0],
                "high": [1.0, 1.0, 1.02, 1.0],
                "low": [1.0, 1.0, 0.98, 1.0],
                "close": [1.0, 1.0, 1.0, 1.0],
                "volume": [1.0, 1.0, 1.0, 1.0],
            },
            index=index,
        )
        signals = pd.DataFrame(
            {"direction": [0, 1, 0, 0], "atr": [np.nan, 0.01, 0.01, 0.01]},
            index=index,
        )

        trades = replay_trades(
            candles,
            signals,
            pair="EURUSD",
            stop_factor=1.0,
            risk_reward=1.0,
        )

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].pair, "EURUSD")
        self.assertEqual(trades[0].outcome, "STOP")
        self.assertEqual(trades[0].result_r, -1.0)

    def test_metrics_are_expressed_in_r(self) -> None:
        trades = [
            self._trade(2.0),
            self._trade(-1.0),
            self._trade(2.0),
        ]

        metrics = calculate_metrics(trades)

        self.assertEqual(metrics["trades"], 3)
        self.assertAlmostEqual(metrics["net_r"], 3.0)
        self.assertAlmostEqual(metrics["profit_factor"], 4.0)
        self.assertAlmostEqual(metrics["expectancy_r"], 1.0)

    def test_ranking_prefers_eligible_sample_before_small_lucky_sample(self) -> None:
        eligible = {
            "eligible": True,
            "net_r": -1.0,
            "expectancy_r": -0.1,
            "profit_factor": 0.9,
            "max_drawdown_r": 3.0,
            "trades": 10,
        }
        lucky = {
            "eligible": False,
            "net_r": 3.0,
            "expectancy_r": 3.0,
            "profit_factor": 999.0,
            "max_drawdown_r": 0.0,
            "trades": 1,
        }

        self.assertGreater(_ranking_key(eligible), _ranking_key(lucky))

    @staticmethod
    def _trade(result_r: float) -> TradeResult:
        return TradeResult(
            pair="EURUSD",
            entry_index=1,
            exit_index=2,
            direction="BUY",
            entry_time="2026-01-01T00:00:00+00:00",
            exit_time="2026-01-01T00:05:00+00:00",
            entry_price=1.0,
            stop=0.9,
            target=1.2,
            exit_price=1.2 if result_r > 0 else 0.9,
            outcome="TARGET" if result_r > 0 else "STOP",
            result_r=result_r,
        )


if __name__ == "__main__":
    unittest.main()
