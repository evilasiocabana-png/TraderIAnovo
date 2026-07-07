import unittest

from application.dynamic_exit_backtest import DynamicExitBacktestEngine
from domain.contracts.dynamic_exit_backtest import DynamicExitBacktestTrade


class DynamicExitBacktestEngineTest(unittest.TestCase):
    def test_empty_backtest_is_readonly_and_safe(self) -> None:
        report = DynamicExitBacktestEngine().run([])

        self.assertEqual(report.status, "SEM_DADOS")
        self.assertTrue(report.read_only)
        self.assertFalse(report.execution_allowed)
        self.assertEqual(report.original.total_trades, 0)
        self.assertEqual(report.dynamic.total_trades, 0)

    def test_compares_original_lab_exit_against_dynamic_exit(self) -> None:
        report = DynamicExitBacktestEngine().run(
            [
                self._trade("ATR_TRAILING_STOP", "TRAIL_BY_ATR", 1.0, 1.4, 120, 150),
                self._trade("BREAK_EVEN", "PROTECT_TO_BREAK_EVEN", -1.0, 0.0, 80, 65),
                self._trade("FIXED_STOP", "KEEP_ORIGINAL_PLAN", 2.0, 1.2, 180, 120),
            ]
        )

        self.assertEqual(report.status, "COMPARADO")
        self.assertEqual(report.original.total_trades, 3)
        self.assertEqual(report.dynamic.total_trades, 3)
        self.assertAlmostEqual(report.original.net_profit_r, 2.0)
        self.assertAlmostEqual(report.dynamic.net_profit_r, 2.6)
        self.assertAlmostEqual(report.original.win_rate, 2 / 3)
        self.assertAlmostEqual(report.dynamic.win_rate, 2 / 3)
        self.assertAlmostEqual(report.dynamic.profit_factor, 2.6)
        self.assertGreater(report.loss_protection_r, 0.0)
        self.assertGreater(report.lost_gain_by_early_exit_r, 0.0)
        self.assertGreater(report.break_even_dominance, 0.0)
        self.assertEqual(report.winner, "DYNAMIC_EXIT")
        self.assertTrue(report.read_only)
        self.assertFalse(report.execution_allowed)

    def test_drawdown_is_calculated_from_equity_curve(self) -> None:
        report = DynamicExitBacktestEngine().run(
            [
                self._trade("FIXED_STOP", "KEEP_ORIGINAL_PLAN", 2.0, 2.0, 10, 10),
                self._trade("FIXED_STOP", "KEEP_ORIGINAL_PLAN", -3.0, -1.0, 10, 10),
                self._trade("FIXED_STOP", "KEEP_ORIGINAL_PLAN", 1.0, 1.0, 10, 10),
            ]
        )

        self.assertAlmostEqual(report.original.max_drawdown_r, 3.0)
        self.assertAlmostEqual(report.dynamic.max_drawdown_r, 1.0)
        self.assertEqual(report.winner, "DYNAMIC_EXIT")

    def _trade(
        self,
        policy: str,
        action: str,
        original_r: float,
        dynamic_r: float,
        original_duration: float,
        dynamic_duration: float,
    ) -> DynamicExitBacktestTrade:
        return DynamicExitBacktestTrade(
            symbol="EURUSD",
            setup="TREND_MOMENTUM",
            timeframe="M1",
            original_policy=policy,
            dynamic_action=action,
            original_result_r=original_r,
            dynamic_result_r=dynamic_r,
            original_duration_minutes=original_duration,
            dynamic_duration_minutes=dynamic_duration,
            planned_rr=2.0,
        )


if __name__ == "__main__":
    unittest.main()
