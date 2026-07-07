"""Testes do resumo Alpha001 exposto no Dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService
from application.research_lab_service import Alpha001ResearchSummaryData


class DashboardAlpha001SummaryTest(unittest.TestCase):
    """Valida resumo estatistico Alpha001 pela fachada do dashboard."""

    def test_dashboard_service_expoe_resumo_vazio(self) -> None:
        """Sem ranking previo, resumo deve ser seguro."""
        summary = DashboardService().get_alpha001_research_summary()

        self.assertIsInstance(summary, Alpha001ResearchSummaryData)
        self.assertEqual(summary.total_experiments, 0)
        self.assertEqual(summary.approval_rate, 0.0)

    def test_dashboard_service_expoe_resumo_apos_ranking(self) -> None:
        """Resumo deve consolidar ranking Alpha001 existente."""
        service = DashboardService()
        service.run_alpha001_parameter_ranking()

        summary = service.get_alpha001_research_summary()

        self.assertGreater(summary.total_experiments, 0)
        self.assertGreaterEqual(summary.total_approved, 0)
        self.assertGreaterEqual(summary.total_rejected, 0)

    def test_dashboard_data_inclui_resumo_alpha001(self) -> None:
        """DashboardData deve carregar resumo estatistico."""
        service = DashboardService()
        service.run_alpha001_parameter_ranking()

        data = service.get_dashboard_data()

        self.assertIsInstance(
            data.alpha001_research_summary,
            Alpha001ResearchSummaryData,
        )

    def test_resumo_expoe_metricas_principais(self) -> None:
        """Resumo deve expor campos exigidos pela UI."""
        service = DashboardService()
        service.run_alpha001_parameter_ranking()

        summary = service.get_alpha001_research_summary()

        self.assertIsInstance(summary.best_profit_factor, float)
        self.assertIsInstance(summary.lowest_max_drawdown_points, float)
        self.assertIsInstance(summary.best_net_profit_points, float)
        self.assertIsInstance(summary.approval_rate, float)

    def test_dashboard_consumindo_apenas_dashboard_service(self) -> None:
        """Dashboard nao deve importar summarizer diretamente."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research.alpha001_research_summary", imports)
        self.assertNotIn("application.research_lab_service", imports)

    def test_dashboard_nao_calcula_estatisticas_diretamente(self) -> None:
        """Dashboard nao deve renderizar resumo demo como pipeline real."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("data.alpha001_research_summary", source)
        self.assertNotIn("total_approved =", source)
        self.assertNotIn("approval_rate =", source)
        self.assertNotIn("Alpha001ResearchSummary", source)

    def _imports(self, caminho: Path) -> set[str]:
        tree = ast.parse(caminho.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
