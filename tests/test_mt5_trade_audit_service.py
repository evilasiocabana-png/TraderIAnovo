import unittest

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.mt5_trade_audit_service import MT5TradeAuditService


class MT5TradeAuditServiceTest(unittest.TestCase):
    def test_audit_report_is_readonly_and_consolidates_signals(self) -> None:
        signals = ForexMT5Service().get_signals()
        lab = LabService().get_latest_result()

        report = MT5TradeAuditService().build_report(signals=signals, lab=lab, positions=[])

        self.assertEqual(report.status, "READ_ONLY")
        self.assertEqual(report.total_rows, len(signals))
        self.assertEqual(report.total_open_positions, 0)
        self.assertTrue(all(row.lab_decision == lab.theoretical_entry for row in report.rows))
        self.assertTrue(
            all(row.dynamic_exit_policy == "ATR_TRAILING_STOP" for row in report.rows)
        )
        self.assertTrue(all(row.dynamic_exit_action for row in report.rows))
        self.assertTrue(
            all(row.dynamic_exit_allowed_to_execute_demo is False for row in report.rows)
        )
