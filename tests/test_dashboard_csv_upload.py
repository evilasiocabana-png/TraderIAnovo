"""Testes de compatibilidade da carga historica no DashboardService."""

from io import BytesIO
from pathlib import Path
import unittest

from application.dashboard_service import DashboardService
from application.replay_service import ReplayData, ReplayStatus


class UploadedCsv(BytesIO):
    """Arquivo em memoria compatível com Streamlit UploadedFile."""

    def __init__(self, content: str, name: str = "historico.csv") -> None:
        super().__init__(content.encode("utf-8"))
        self.name = name

    def getvalue(self) -> bytes:
        """Retorna o conteudo para simular UploadedFile."""
        return super().getvalue()


class DashboardCsvUploadTest(unittest.TestCase):
    """Valida carga historica via objeto enviado a fachada."""

    def test_dashboard_service_carrega_upload_csv_valido(self) -> None:
        data = DashboardService().load_historical_replay_csv(
            self._uploaded_csv(3),
        )

        self.assertIsInstance(data, ReplayData)
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.total_candles, 3)

    def test_dashboard_service_rejeita_upload_csv_invalido(self) -> None:
        data = DashboardService().load_historical_replay_csv(
            UploadedCsv("foo,bar\n1,2\n"),
        )

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertEqual(data.total_candles, 0)

    def test_dashboard_nao_usa_upload_csv_historico(self) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("st.file_uploader", source)
        self.assertNotIn("Selecionar CSV historico", source)
        self.assertNotIn("Carregar CSV Historico", source)

    def test_dashboard_seleciona_dataset_por_fachada(self) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("service.list_historical_datasets()", source)
        self.assertIn("service.select_historical_dataset", source)
        self.assertIn("service.get_selected_historical_dataset()", source)

    def test_dashboard_nao_importa_loader_ou_csv(self) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("HistoricalDataLoader", source)
        self.assertNotIn("csv.", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("load_historical_replay_csv", source)

    def test_carregamento_demo_permanece_compativel(self) -> None:
        data = DashboardService().load_demo_replay_candles()

        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertGreater(data.total_candles, 0)

    def _uploaded_csv(self, quantity: int) -> UploadedCsv:
        lines = ["datetime,open,high,low,close,volume"]
        for index in range(quantity):
            close = 100.0 + index
            lines.append(
                f"2026-06-26 09:{index:02d},"
                f"{close - 1},{close + 2},{close - 2},{close},1000"
            )
        return UploadedCsv("\n".join(lines) + "\n")


if __name__ == "__main__":
    unittest.main()
