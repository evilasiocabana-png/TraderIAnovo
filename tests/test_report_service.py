import unittest

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.report_service import ReportService


class ReportServiceTest(unittest.TestCase):
    def test_builds_rows_from_forex_and_lab(self) -> None:
        forex = ForexMT5Service().get_status()
        lab = LabService().get_latest_result()

        rows = ReportService().build_rows(forex=forex, lab=lab)
        sections = {row.section for row in rows}

        self.assertEqual(len(rows), 2)
        self.assertEqual(sections, {"Forex MT5", "Lab"})
