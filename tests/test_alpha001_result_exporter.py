"""Testes do exportador de resultados Alpha 001."""

import unittest

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)
from research.alpha001_result_exporter import Alpha001ResultExporter


class Alpha001ResultExporterTest(unittest.TestCase):
    """Valida conversao de resultados para estruturas exportaveis."""

    def test_to_dict_exporta_parametros_e_metricas(self) -> None:
        """Exportacao em dict deve conter campos obrigatorios."""
        rows = Alpha001ResultExporter().to_dict([self._result()])

        self.assertEqual(rows[0]["opening_range_minutes"], 15)
        self.assertEqual(rows[0]["minimum_range_size"], 20.0)
        self.assertEqual(rows[0]["minimum_volume"], 1000)
        self.assertEqual(rows[0]["total_trades"], 10)
        self.assertEqual(rows[0]["validation_status"], "APPROVED")

    def test_to_dict_inclui_recommendation(self) -> None:
        """Exportacao deve incluir recomendacao textual."""
        rows = Alpha001ResultExporter().to_dict([self._result()])

        self.assertEqual(
            rows[0]["recommendation"],
            "READY_FOR_EXTENDED_RESEARCH",
        )

    def test_to_csv_rows_inclui_header(self) -> None:
        """Linhas CSV devem iniciar com cabecalho."""
        rows = Alpha001ResultExporter().to_csv_rows([self._result()])

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

    def test_to_csv_rows_exporta_valores(self) -> None:
        """Linhas CSV devem conter valores na ordem do cabecalho."""
        rows = Alpha001ResultExporter().to_csv_rows([self._result()])

        self.assertEqual(rows[1][0], 15)
        self.assertEqual(rows[1][5], 1.8)
        self.assertEqual(rows[1][8], "APPROVED")
        self.assertEqual(rows[1][9], "READY_FOR_EXTENDED_RESEARCH")

    def test_recommendation_para_rejeicao(self) -> None:
        """Status rejeitados devem gerar recomendacoes coerentes."""
        result = self._result(status="INSUFFICIENT_SAMPLE")

        rows = Alpha001ResultExporter().to_dict([result])

        self.assertEqual(rows[0]["recommendation"], "COLLECT_MORE_SAMPLES")

    def test_lista_vazia_retorna_estruturas_seguras(self) -> None:
        """Exportador deve aceitar lista vazia."""
        exporter = Alpha001ResultExporter()

        self.assertEqual(exporter.to_dict([]), [])
        self.assertEqual(len(exporter.to_csv_rows([])), 1)

    def _result(
        self,
        status: str = "APPROVED",
    ) -> Alpha001ParameterSweepResult:
        return Alpha001ParameterSweepResult(
            parameters=Alpha001ParameterSet(
                opening_range_minutes=15,
                minimum_range_size=20.0,
                minimum_volume=1000,
            ),
            total_trades=10,
            win_rate=0.6,
            profit_factor=1.8,
            max_drawdown_points=35.0,
            net_profit_points=120.0,
            validation_status=status,
        )


if __name__ == "__main__":
    unittest.main()
