"""Testes da integracao do ResearchReport ao Dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardData, DashboardService
from application.research_lab_service import ResearchReportData


class DashboardResearchReportTest(unittest.TestCase):
    """Valida exposicao do ResearchReport pela fachada do dashboard."""

    def test_dashboard_service_expoe_research_report(self) -> None:
        service = DashboardService()
        service.run_demo_alpha001_experiment()

        report = service.get_research_report()

        self.assertIsInstance(report, ResearchReportData)
        self.assertIn(report.conclusion, {"ACCEPTABLE", "REJECTED", "INCONCLUSIVE"})

    def test_dashboard_data_inclui_research_report(self) -> None:
        service = DashboardService()
        service.run_demo_alpha001_experiment()

        data = service.get_dashboard_data()

        self.assertIsInstance(data, DashboardData)
        self.assertIsInstance(data.research_report, ResearchReportData)

    def test_dashboard_app_usa_apenas_dashboard_service(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research.research_report", imports)
        self.assertNotIn("application.research_lab_service", imports)

    def test_dashboard_renderiza_research_report_sem_calcular_metricas(self) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("exibir_research_report", source)
        self.assertIn("research_report", source)
        self.assertNotIn("ResearchReport(", source)
        self.assertNotIn("Alpha001Experiment(", source)

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
