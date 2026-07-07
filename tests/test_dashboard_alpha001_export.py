"""Testes da exportacao CSV Alpha001 via DashboardService."""

import ast
import tempfile
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService


class DashboardAlpha001ExportTest(unittest.TestCase):
    """Valida exportacao CSV Alpha001 pela fachada do dashboard."""

    def test_dashboard_service_exporta_csv_alpha001(self) -> None:
        """DashboardService deve delegar exportacao para application service."""
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "alpha001.csv"
            service = DashboardService()
            service.run_alpha001_parameter_ranking()

            exported_path = service.export_alpha001_results_to_csv(output_path)

            self.assertEqual(exported_path, output_path)
            self.assertTrue(output_path.exists())

    def test_nao_exporta_automaticamente_ao_abrir_dashboard_data(self) -> None:
        """Abertura do dashboard nao deve gravar arquivo automaticamente."""
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "alpha001.csv"
            service = DashboardService()

            service.get_dashboard_data()

            self.assertFalse(output_path.exists())

    def test_dashboard_app_consumindo_apenas_dashboard_service(self) -> None:
        """Dashboard nao deve importar servicos internos de pesquisa."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("application.research_lab_service", imports)
        self.assertNotIn("research.alpha001_result_exporter", imports)

    def test_dashboard_tem_acao_explicita_de_exportacao(self) -> None:
        """UI deve ter botao explicito para exportar CSV."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("Exportar CSV Alpha001", source)
        self.assertIn("service.export_alpha001_results_to_csv", source)
        self.assertIn("st.success", source)
        self.assertIn("st.error", source)

    def test_dashboard_nao_duplica_logica_de_exportacao(self) -> None:
        """Dashboard nao deve converter resultados manualmente."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("Alpha001ResultExporter", source)
        self.assertNotIn("to_csv_rows", source)
        self.assertNotIn("csv.writer", source)

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
