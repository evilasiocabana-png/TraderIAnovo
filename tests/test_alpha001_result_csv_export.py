"""Testes da persistencia CSV opcional dos resultados Alpha001."""

import csv
import tempfile
import unittest
from pathlib import Path

from application.research_lab_service import ResearchLabService


class Alpha001ResultCsvExportTest(unittest.TestCase):
    """Valida exportacao CSV pela camada de aplicacao."""

    def test_nao_salva_automaticamente_ao_gerar_ranking(self) -> None:
        """Ranking nao deve criar arquivo sem chamada explicita."""
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "alpha001.csv"
            service = ResearchLabService()

            service.run_alpha001_parameter_ranking()

            self.assertFalse(output_path.exists())

    def test_exporta_csv_para_caminho_recebido(self) -> None:
        """Exportacao deve usar caminho informado por parametro."""
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "alpha001.csv"
            service = ResearchLabService()
            service.run_alpha001_parameter_ranking()

            returned_path = service.export_alpha001_results_to_csv(output_path)

            self.assertEqual(returned_path, output_path)
            self.assertTrue(output_path.exists())

    def test_csv_contem_header_do_exporter(self) -> None:
        """CSV deve conter estrutura exportavel oficial."""
        rows = self._exported_rows()

        self.assertEqual(
            rows[0],
            [
                "opening_range_minutes",
                "minimum_range_size",
                "minimum_volume",
                "total_trades",
                "win_rate",
                "profit_factor",
                "max_drawdown_points",
                "net_profit_points",
                "validation_status",
                "recommendation",
            ],
        )

    def test_csv_contem_resultados_do_ranking(self) -> None:
        """CSV deve persistir as metricas exportaveis."""
        rows = self._exported_rows()

        self.assertGreater(len(rows), 1)
        self.assertEqual(rows[1][8], "APPROVED")
        self.assertEqual(rows[1][9], "READY_FOR_EXTENDED_RESEARCH")

    def test_exportacao_sem_ranking_gera_apenas_header(self) -> None:
        """Sem ranking previo, exportacao nao executa pesquisa automaticamente."""
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "empty.csv"
            service = ResearchLabService()

            service.export_alpha001_results_to_csv(output_path)

            with output_path.open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.reader(csv_file))
        self.assertEqual(len(rows), 1)

    def test_service_reutiliza_alpha001_result_exporter(self) -> None:
        """Service deve delegar a conversao para o exporter oficial."""
        source = Path("application/research_lab_service.py").read_text(
            encoding="utf-8",
        )

        self.assertIn("Alpha001ResultExporter", source)
        self.assertIn("to_csv_rows", source)

    def _exported_rows(self) -> list[list[str]]:
        with tempfile.TemporaryDirectory() as folder:
            output_path = Path(folder) / "alpha001.csv"
            service = ResearchLabService()
            service.run_alpha001_parameter_ranking()
            service.export_alpha001_results_to_csv(output_path)
            with output_path.open(encoding="utf-8", newline="") as csv_file:
                return list(csv.reader(csv_file))


if __name__ == "__main__":
    unittest.main()
