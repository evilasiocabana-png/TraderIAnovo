import unittest

from application.dashboard_service import DashboardService


class DashboardServiceTest(unittest.TestCase):
    def test_instantiates_without_error(self) -> None:
        service = DashboardService()

        self.assertIsInstance(service, DashboardService)

    def test_exposes_forex_lab_and_report_views(self) -> None:
        service = DashboardService()
        view_model = service.get_dashboard_view_model()

        self.assertIn("forex_mt5", view_model)
        self.assertIn("lab", view_model)
        self.assertIn("report", view_model)

    def test_report_consolidates_lab_and_forex_mt5(self) -> None:
        service = DashboardService()
        report = service.get_report_view()
        sections = {row["section"] for row in report["rows"]}

        self.assertIn("Forex MT5", sections)
        self.assertIn("Lab", sections)
