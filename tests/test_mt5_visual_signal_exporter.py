import unittest

from application.dashboard_view_model import (
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
)
from application.mt5_visual_signal_exporter import MT5VisualSignalExporter


class MT5VisualSignalExporterTest(unittest.TestCase):
    def test_dashboard_exposes_readonly_visual_payload(self) -> None:
        payload = MT5VisualSignalExporter().build_payload(
            DashboardMT5ForexSignalViewModel(
                pairs=[DashboardMT5ForexSignalRowViewModel(pair="EURUSD")]
            )
        )

        self.assertEqual(payload["mode"], "VISUAL_ONLY")
        self.assertIs(payload["read_only"], True)
        self.assertIs(payload["execution_allowed"], False)
        self.assertGreaterEqual(len(payload["signals"]), 1)
