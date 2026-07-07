import unittest

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.report_service import ReportService
from domain.contracts.trade_audit import TradeAuditReport


class ReportServiceTest(unittest.TestCase):
    def test_builds_rows_from_forex_and_lab(self) -> None:
        forex = ForexMT5Service().get_status()
        lab = LabService().get_latest_result()

        rows = ReportService().build_rows(forex=forex, lab=lab)
        sections = {row.section for row in rows}

        self.assertEqual(len(rows), 2)
        self.assertEqual(sections, {"Forex MT5", "Lab"})
        lab_row = next(row for row in rows if row.section == "Lab")
        self.assertEqual(lab_row.dynamic_exit_policy, lab.stop_management)
        self.assertEqual(lab_row.dynamic_exit_action, "KEEP_ORIGINAL_PLAN")
        self.assertEqual(lab_row.dynamic_exit_market_state, "NO_POSITION")
        self.assertEqual(lab_row.dynamic_exit_executed_action, "NONE")
        self.assertEqual(lab_row.dynamic_exit_final_result, "OBSERVADO_READ_ONLY")
        self.assertIs(lab_row.dynamic_exit_allowed_to_execute_demo, False)

    def test_summary_exposes_dynamic_exit_readonly_contract(self) -> None:
        forex = ForexMT5Service().get_status()
        lab = LabService().get_latest_result()
        summary = ReportService().build_summary(
            forex=forex,
            lab=lab,
            audit=TradeAuditReport(
                status="READ_ONLY",
                source="test",
                total_rows=0,
                rows=[],
                message="test",
            ),
        )

        self.assertEqual(summary["dynamic_exit_policy"], lab.stop_management)
        self.assertEqual(summary["dynamic_exit_action"], "KEEP_ORIGINAL_PLAN")
        self.assertEqual(summary["dynamic_exit_market_state"], "NO_POSITION")
        self.assertEqual(summary["dynamic_exit_executed_action"], "NONE")
        self.assertEqual(summary["dynamic_exit_final_result"], "OBSERVADO_READ_ONLY")
        self.assertIs(summary["dynamic_exit_allowed_to_execute_demo"], False)
