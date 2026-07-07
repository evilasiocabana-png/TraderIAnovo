import unittest

from application.dashboard_service import DashboardService


class MT5VisualSignalExporterTest(unittest.TestCase):
    def test_dashboard_exposes_readonly_visual_payload(self) -> None:
        payload = DashboardService().get_mt5_visual_signal_payload()

        self.assertEqual(payload["mode"], "VISUAL_ONLY")
        self.assertIs(payload["read_only"], True)
        self.assertIs(payload["execution_allowed"], False)
        self.assertGreaterEqual(len(payload["signals"]), 1)
