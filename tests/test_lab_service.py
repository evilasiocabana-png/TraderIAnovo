import unittest

from application.lab_service import LabService


class LabServiceTest(unittest.TestCase):
    def test_returns_theoretical_parameters(self) -> None:
        result = LabService().get_latest_result()

        self.assertEqual(result.setup, "TREND_MOMENTUM")
        self.assertEqual(result.timeframe, "M1")
        self.assertEqual(result.theoretical_entry, "WAIT")
        self.assertEqual(result.stop_management, "ATR_TRAILING_STOP")
