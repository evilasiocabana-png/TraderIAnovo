"""Testes da carga de dataset historico via DashboardService."""

import ast
import tempfile
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService
from application.replay_service import ReplayData, ReplayStatus


class DashboardHistoricalDatasetTest(unittest.TestCase):
    """Valida datasets historicos expostos ao Dashboard."""

    def test_dashboard_service_carrega_dataset_historico(self) -> None:
        """Fachada deve carregar CSV historico no replay."""
        data = DashboardService().load_historical_replay_csv(
            self._historical_csv(3),
        )

        self.assertIsInstance(data, ReplayData)
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.total_candles, 3)

    def test_replay_recebe_candles_historicos(self) -> None:
        """ReplayData deve expor candles historicos carregados."""
        service = DashboardService()

        service.load_historical_replay_csv(self._historical_csv(2))
        data = service.get_dashboard_data().replay_data

        self.assertEqual(data.total_candles, 2)
        self.assertEqual(len(data.candles_loaded), 2)
        self.assertEqual(data.candles_loaded[0].data, "2026-06-26 09:00")

    def test_dados_demo_continuam_funcionando(self) -> None:
        """Carga demo deve permanecer operacional."""
        data = DashboardService().load_demo_replay_candles()

        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertGreater(data.total_candles, 0)

    def test_dataset_invalido_retorna_erro_seguro(self) -> None:
        """CSV invalido nao deve lançar excecao pela fachada."""
        data = DashboardService().load_historical_replay_csv(self._invalid_csv())

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertEqual(data.total_candles, 0)
        self.assertEqual(data.candles_loaded, [])

    def test_dashboard_consumindo_apenas_dashboard_service(self) -> None:
        """Dashboard nao deve importar loader historico diretamente."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("data.historical_data_loader", imports)

    def test_dashboard_data_expoe_dataset_ativo_certificado(self) -> None:
        """DashboardData deve trazer dataset ativo pela camada de aplicacao."""
        data = DashboardService().get_dashboard_data()

        self.assertIsNotNone(data.active_dataset)
        self.assertEqual(data.active_dataset.asset, "PETR4")
        self.assertEqual(data.active_dataset.timeframe, "1d")
        self.assertEqual(data.active_dataset.provider, "HistoricalDataProvider")
        self.assertEqual(data.active_dataset.source, "Yahoo Finance")
        self.assertEqual(data.active_dataset.candles, 2491)
        self.assertEqual(
            data.active_dataset.dataset_certification,
            "PETR4_DATASET_CERTIFIED_FOR_QUANTITATIVE_RESEARCH",
        )
        self.assertEqual(data.active_dataset.replay_status, "Pronto para Replay")
        self.assertEqual(
            data.active_dataset.research_status,
            "Pronto para Research Lab",
        )

    def test_dashboard_data_lista_datasets_disponiveis(self) -> None:
        """DashboardData deve destacar dataset ativo entre os disponiveis."""
        datasets = DashboardService().get_dashboard_data().available_datasets

        self.assertGreaterEqual(len(datasets), 1)
        selected = [dataset for dataset in datasets if dataset.selected]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].asset, "PETR4")
        self.assertTrue(
            all(dataset.provider == "HistoricalDataProvider" for dataset in datasets)
        )

    def test_dashboard_data_expoe_perfil_quantitativo_petr4(self) -> None:
        """DashboardData deve trazer perfil quantitativo real do dataset PETR4."""
        profile = DashboardService().get_dashboard_data().dataset_profile

        self.assertIsNotNone(profile)
        self.assertEqual(profile.asset, "PETR4")
        self.assertEqual(profile.timeframe, "1d")
        self.assertEqual(profile.candles, 2491)
        self.assertAlmostEqual(profile.initial_price, 9.199999809265137)
        self.assertAlmostEqual(profile.final_price, 38.060001373291016)
        self.assertGreater(profile.accumulated_return, 3.0)
        self.assertGreater(profile.annualized_return, 0.0)
        self.assertGreater(profile.annualized_volatility, 0.0)
        self.assertGreater(profile.max_drawdown, 0.0)
        self.assertLessEqual(profile.max_drawdown, 1.0)
        self.assertEqual(profile.best_day, "2020-03-13 00:00:00")
        self.assertEqual(profile.worst_day, "2020-03-09 00:00:00")
        self.assertEqual(profile.positive_days, 1303)
        self.assertEqual(profile.negative_days, 1153)
        self.assertGreater(profile.average_volume, 0.0)
        self.assertEqual(profile.max_volume, 490230400)
        self.assertEqual(profile.quality_status, "APPROVED")
        self.assertEqual(len(profile.price_curve), 2491)
        self.assertEqual(len(profile.accumulated_return_curve), 2491)
        self.assertEqual(len(profile.daily_return_histogram), 12)
        self.assertEqual(len(profile.volume_curve), 2491)

    def test_replay_seleciona_e_carrega_dataset_petr4_estrutural(self) -> None:
        """Replay deve carregar PETR4 pelo mesmo provider estrutural do painel."""
        service = DashboardService()

        selected = service.select_historical_dataset(
            "b3_petr4_1d_raw_yahoo_chart_20160628_20260628",
        )
        replay_data = service.load_selected_historical_dataset_to_replay()

        self.assertEqual(selected.ativo, "PETR4")
        self.assertEqual(selected.timeframe, "1d")
        self.assertEqual(selected.estimated_candles, 2491)
        self.assertEqual(replay_data.status, ReplayStatus.READY)
        self.assertEqual(replay_data.total_candles, 2491)

    def test_dashboard_nao_duplica_logica_de_importacao(self) -> None:
        """Dashboard deve selecionar datasets sem abrir origem fisica."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("service.list_historical_datasets()", source)
        self.assertIn("service.select_historical_dataset", source)
        self.assertIn("service.get_selected_historical_dataset()", source)
        self.assertNotIn("service.load_historical_replay_csv", source)
        self.assertNotIn("HistoricalDataLoader", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("csv.", source)

    def _historical_csv(self, quantity: int) -> Path:
        lines = ["datetime,open,high,low,close,volume"]
        for index in range(quantity):
            close = 100.0 + index
            lines.append(
                f"2026-06-26 09:{index:02d},"
                f"{close - 1},{close + 2},{close - 2},{close},1000"
            )
        return self._csv("\n".join(lines) + "\n")

    def _invalid_csv(self) -> Path:
        return self._csv("foo,bar\n1,2\n")

    def _csv(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
            newline="",
        )
        with handle:
            handle.write(content)
        return Path(handle.name)

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
