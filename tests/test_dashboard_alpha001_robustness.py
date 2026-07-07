"""Testes da robustez Alpha001 exposta no Dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService
from application.research_lab_service import Alpha001RobustnessData


class DashboardAlpha001RobustnessTest(unittest.TestCase):
    """Valida analise de robustez Alpha001 via DashboardService."""

    def test_dashboard_service_expoe_robustez_vazia(self) -> None:
        """Sem ranking previo, robustez deve ser inconclusiva."""
        robustness = DashboardService().get_alpha001_robustness()

        self.assertIsInstance(robustness, Alpha001RobustnessData)
        self.assertEqual(robustness.status, "INCONCLUSIVE")
        self.assertEqual(robustness.robustness_score, 0.0)

    def test_dashboard_service_expoe_robustez_apos_ranking(self) -> None:
        """Robustez deve usar resultados ja existentes do ranking."""
        service = DashboardService()
        service.run_alpha001_parameter_ranking()

        robustness = service.get_alpha001_robustness()

        self.assertIsInstance(robustness.robustness_score, float)
        self.assertIn(robustness.status, {"ROBUST", "FRAGILE", "INCONCLUSIVE"})
        self.assertTrue(robustness.reasons)

    def test_dashboard_data_inclui_robustez(self) -> None:
        """DashboardData deve carregar robustez Alpha001."""
        service = DashboardService()
        service.run_alpha001_parameter_ranking()

        data = service.get_dashboard_data()

        self.assertIsInstance(data.alpha001_robustness, Alpha001RobustnessData)

    def test_robustez_expoe_score_status_reasons(self) -> None:
        """Robustez deve expor campos exigidos pela UI."""
        robustness = DashboardService().get_alpha001_robustness()

        self.assertIsInstance(robustness.robustness_score, float)
        self.assertIsInstance(robustness.status, str)
        self.assertIsInstance(robustness.reasons, list)

    def test_dashboard_consumindo_apenas_dashboard_service(self) -> None:
        """Dashboard nao deve importar analyzer diretamente."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research.alpha001_robustness_analyzer", imports)
        self.assertNotIn("application.research_lab_service", imports)

    def test_dashboard_nao_calcula_robustez_diretamente(self) -> None:
        """Dashboard nao deve renderizar robustez demo como pipeline real."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("data.alpha001_robustness", source)
        self.assertNotIn("Alpha001RobustnessAnalyzer", source)
        self.assertNotIn("robustness_score =", source)

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
