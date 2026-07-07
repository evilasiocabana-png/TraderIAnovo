"""Testes dos filtros Alpha001 no Dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService
from application.research_lab_service import Alpha001ParameterRankingData


class DashboardAlpha001FiltersTest(unittest.TestCase):
    """Valida filtros de ranking Alpha001 pela fachada do dashboard."""

    def test_filtra_all(self) -> None:
        """ALL deve retornar ranking original."""
        service = self._service_with_ranking()

        filtered = service.filter_alpha001_parameter_ranking("ALL")

        self.assertEqual(filtered, service.list_alpha001_parameter_ranking())

    def test_filtra_approved(self) -> None:
        """APPROVED deve retornar apenas aprovados."""
        service = self._service_with_ranking()

        filtered = service.filter_alpha001_parameter_ranking("APPROVED")

        self.assertTrue(filtered)
        self.assertTrue(
            all(item.validation_status == "APPROVED" for item in filtered)
        )

    def test_filtra_rejected(self) -> None:
        """REJECTED deve retornar somente nao aprovados."""
        service = self._service_with_mixed_ranking()

        filtered = service.filter_alpha001_parameter_ranking("REJECTED")

        self.assertEqual(len(filtered), 2)
        self.assertTrue(
            all(item.validation_status != "APPROVED" for item in filtered)
        )

    def test_filtra_insufficient_sample(self) -> None:
        """INSUFFICIENT_SAMPLE deve filtrar status especifico."""
        service = self._service_with_mixed_ranking()

        filtered = service.filter_alpha001_parameter_ranking(
            "INSUFFICIENT_SAMPLE",
        )

        self.assertEqual(len(filtered), 1)
        self.assertTrue(
            all(
                item.validation_status == "INSUFFICIENT_SAMPLE"
                for item in filtered
            )
        )

    def test_filtro_nao_altera_ranking_original(self) -> None:
        """Filtro deve atuar sobre copia sem alterar ranking armazenado."""
        service = self._service_with_ranking()
        original = service.list_alpha001_parameter_ranking()

        service.filter_alpha001_parameter_ranking("APPROVED")

        self.assertEqual(service.list_alpha001_parameter_ranking(), original)

    def test_dashboard_consumindo_apenas_dashboard_service(self) -> None:
        """Dashboard nao deve importar modulos de ranking/filtro."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research.alpha001_parameter_ranking", imports)
        self.assertNotIn("application.research_lab_service", imports)

    def test_dashboard_nao_recalcula_metricas(self) -> None:
        """Dashboard deve chamar filtro da fachada sem recalculo local."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("service.filter_alpha001_parameter_ranking", source)
        self.assertNotIn("profit_factor =", source)
        self.assertNotIn("max_drawdown_points =", source)

    def _service_with_ranking(self) -> DashboardService:
        service = DashboardService()
        service.run_alpha001_parameter_ranking()
        return service

    def _service_with_mixed_ranking(self) -> DashboardService:
        service = DashboardService()
        service.research_lab_service.alpha001_ranking_results = [
            self._ranking_data("APPROVED"),
            self._ranking_data("INSUFFICIENT_SAMPLE"),
            self._ranking_data("LOW_PROFIT_FACTOR"),
        ]
        return service

    def _ranking_data(self, status: str) -> Alpha001ParameterRankingData:
        return Alpha001ParameterRankingData(
            opening_range_minutes=15,
            minimum_range_size=20.0,
            minimum_volume=1000,
            total_trades=1,
            win_rate=1.0,
            profit_factor=1.5,
            max_drawdown_points=0.0,
            net_profit_points=100.0,
            validation_status=status,
        )

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
