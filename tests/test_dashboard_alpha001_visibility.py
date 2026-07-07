"""Testes de visibilidade da Alpha 001 no dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService


class DashboardAlpha001VisibilityTest(unittest.TestCase):
    """Valida exposicao da Alpha 001 via camada application."""

    def test_alpha001_aparece_na_lista_de_estrategias_disponiveis(self) -> None:
        """DashboardService deve listar Alpha 001 para Research Lab."""
        strategies = DashboardService().list_available_research_strategies()

        self.assertIn("alpha001_iorb", strategies)

    def test_dashboard_service_expoe_alpha001_corretamente(self) -> None:
        """DashboardData deve carregar estrategias disponiveis."""
        data = DashboardService().get_dashboard_data()

        self.assertIn("alpha001_iorb", data.available_research_strategies)

    def test_dashboard_nao_tem_dependencia_direta_de_strategy_ou_research(
        self,
    ) -> None:
        """Dashboard deve depender apenas da fachada de aplicacao."""
        imports = self._dashboard_imports()

        self.assertNotIn("strategies.strategy_factory", imports)
        self.assertNotIn("strategies.alpha001_iorb_strategy", imports)
        self.assertNotIn("research.research_lab", imports)

    def test_estrategias_existentes_continuam_aparecendo(self) -> None:
        """Catalogo exposto deve manter estrategias anteriores."""
        strategies = DashboardService().list_available_research_strategies()

        self.assertIn("breakout", strategies)
        self.assertIn("pullback", strategies)
        self.assertIn("score_contexto", strategies)
        self.assertIn("smart_money", strategies)

    def _dashboard_imports(self) -> set[str]:
        tree = ast.parse(Path("dashboard_app.py").read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
