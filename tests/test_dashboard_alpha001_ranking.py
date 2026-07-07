"""Testes de exposicao do ranking Alpha001 no Dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService
from application.research_lab_service import Alpha001ParameterRankingData


class DashboardAlpha001RankingTest(unittest.TestCase):
    """Valida ranking Alpha001 exposto pela camada de aplicacao."""

    def test_dashboard_service_expoe_ranking_alpha001(self) -> None:
        """DashboardService deve executar e listar ranking Alpha001."""
        service = DashboardService()

        ranking = service.run_alpha001_parameter_ranking()

        self.assertTrue(ranking)
        self.assertIsInstance(ranking[0], Alpha001ParameterRankingData)
        self.assertEqual(service.list_alpha001_parameter_ranking(), ranking)

    def test_dashboard_data_inclui_ranking_alpha001(self) -> None:
        """DashboardData deve carregar ranking ja calculado."""
        service = DashboardService()
        ranking = service.run_alpha001_parameter_ranking()

        data = service.get_dashboard_data()

        self.assertEqual(data.alpha001_parameter_ranking, ranking)

    def test_melhor_configuracao_fica_no_topo(self) -> None:
        """Primeiro item deve respeitar ranking vindo da aplicacao."""
        ranking = DashboardService().run_alpha001_parameter_ranking()

        self.assertEqual(ranking[0].validation_status, "APPROVED")
        self.assertGreaterEqual(
            ranking[0].profit_factor,
            ranking[-1].profit_factor,
        )

    def test_ranking_expoe_metricas_principais(self) -> None:
        """Ranking deve expor metricas necessarias ao dashboard."""
        result = DashboardService().run_alpha001_parameter_ranking()[0]

        self.assertIsInstance(result.profit_factor, float)
        self.assertIsInstance(result.max_drawdown_points, float)
        self.assertIsInstance(result.net_profit_points, float)
        self.assertIsInstance(result.total_trades, int)
        self.assertIsInstance(result.validation_status, str)

    def test_dashboard_nao_importa_ranking_diretamente(self) -> None:
        """Dashboard deve depender apenas de DashboardService."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research.alpha001_parameter_ranking", imports)
        self.assertNotIn("research.alpha001_parameter_sweep", imports)

    def test_dashboard_nao_renderiza_ranking_demo_como_research_real(self) -> None:
        """Dashboard nao deve expor ranking demo como pipeline real."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("service.run_alpha001_parameter_ranking()", source)
        self.assertNotIn("Alpha001ParameterRanking(", source)

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
