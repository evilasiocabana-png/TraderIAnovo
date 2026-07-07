import unittest

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.mt5_trade_audit_service import MT5TradeAuditService


class MT5TradeAuditServiceTest(unittest.TestCase):
    def test_audit_report_is_readonly_and_consolidates_signals(self) -> None:
        signals = ForexMT5Service().get_signals()
        lab = LabService().get_latest_result()

        report = MT5TradeAuditService().build_report(signals=signals, lab=lab)

        self.assertEqual(report.status, "READ_ONLY")
        self.assertEqual(report.total_rows, len(signals))
        self.assertTrue(all(row.lab_decision == lab.theoretical_entry for row in report.rows))
