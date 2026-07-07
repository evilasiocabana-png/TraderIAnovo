import unittest

from application.dynamic_exit_paper_simulation import DynamicExitPaperSimulationEngine
from domain.contracts.dynamic_exit_paper import DynamicExitPaperRecommendationRecord


class DynamicExitPaperSimulationEngineTest(unittest.TestCase):
    def test_empty_simulation_is_readonly_and_safe(self) -> None:
        report = DynamicExitPaperSimulationEngine().run([])

        self.assertEqual(report.status, "SEM_DADOS")
        self.assertTrue(report.read_only)
        self.assertFalse(report.execution_allowed)
        self.assertEqual(report.total_recommendations, 0)
        self.assertIsNotNone(report.comparison)
        self.assertEqual(report.comparison.status, "SEM_DADOS")

    def test_records_recommendations_without_execution(self) -> None:
        report = DynamicExitPaperSimulationEngine().run(
            [
                self._record("ATR_TRAILING_STOP", "TRAIL_BY_ATR", 1.0, 1.5),
                self._record("BREAK_EVEN", "PROTECT_TO_BREAK_EVEN", -1.0, 0.0),
            ]
        )

        self.assertEqual(report.status, "SIMULADO")
        self.assertEqual(report.total_recommendations, 2)
        self.assertEqual(report.simulated_actions["TRAIL_BY_ATR"], 1)
        self.assertEqual(report.simulated_actions["PROTECT_TO_BREAK_EVEN"], 1)
        self.assertTrue(all(record.executed is False for record in report.records))
        self.assertTrue(report.read_only)
        self.assertFalse(report.execution_allowed)

    def test_compares_original_result_with_dynamic_paper_result(self) -> None:
        report = DynamicExitPaperSimulationEngine().run(
            [
                self._record("ATR_TRAILING_STOP", "TRAIL_BY_ATR", 1.0, 1.5),
                self._record("BREAK_EVEN", "PROTECT_TO_BREAK_EVEN", -1.0, 0.0),
                self._record("FIXED_STOP", "KEEP_ORIGINAL_PLAN", 2.0, 1.0),
            ]
        )

        self.assertIsNotNone(report.comparison)
        assert report.comparison is not None
        self.assertEqual(report.comparison.status, "COMPARADO")
        self.assertAlmostEqual(report.comparison.original.net_profit_r, 2.0)
        self.assertAlmostEqual(report.comparison.dynamic.net_profit_r, 2.5)
        self.assertGreater(report.comparison.loss_protection_r, 0.0)
        self.assertGreater(report.comparison.lost_gain_by_early_exit_r, 0.0)
        self.assertEqual(report.comparison.winner, "DYNAMIC_EXIT")

    def test_forces_record_to_readonly_even_if_input_claims_execution(self) -> None:
        report = DynamicExitPaperSimulationEngine().run(
            [
                self._record(
                    "ATR_TRAILING_STOP",
                    "TRAIL_BY_ATR",
                    1.0,
                    1.5,
                    executed=True,
                )
            ]
        )

        self.assertFalse(report.records[0].executed)
        self.assertFalse(report.execution_allowed)

    def _record(
        self,
        policy: str,
        action: str,
        original_r: float,
        dynamic_r: float,
        *,
        executed: bool = False,
    ) -> DynamicExitPaperRecommendationRecord:
        return DynamicExitPaperRecommendationRecord(
            symbol="EURUSD",
            setup="TREND_MOMENTUM",
            timeframe="M1",
            original_policy=policy,
            dynamic_action=action,
            dynamic_reason="Read-only test recommendation.",
            dynamic_confidence=0.65,
            market_state="TREND_RUNNER",
            original_result_r=original_r,
            dynamic_paper_result_r=dynamic_r,
            original_duration_minutes=100.0,
            dynamic_duration_minutes=80.0,
            planned_rr=2.0,
            executed=executed,
        )


if __name__ == "__main__":
    unittest.main()
