"""Smoke tests dos paineis do Dashboard via DashboardService."""

import unittest

from application.dashboard_service import DashboardData, DashboardService


class DashboardSmokeTest(unittest.TestCase):
    """Valida carregamento seguro dos dados das abas do dashboard."""

    def test_home_carrega_corretamente(self) -> None:
        """Home deve expor status basico do sistema."""
        data = DashboardService().get_dashboard_data()

        self.assertIsNotNone(data.system_status)
        self.assertTrue(data.system_status.active_symbol)
        self.assertTrue(data.system_status.version)

    def test_market_dna_carrega_corretamente(self) -> None:
        """Market DNA deve carregar snapshot ou fallback seguro."""
        data = DashboardService().get_dashboard_data()

        self.assertTrue(hasattr(data, "market_snapshot"))
        self.assertTrue(hasattr(data, "strategy_signal"))
        self.assertTrue(hasattr(data, "regime_data"))
        self.assertTrue(hasattr(data, "research_data"))

    def test_replay_carrega_corretamente(self) -> None:
        """Replay deve expor DTO seguro mesmo sem candles carregados."""
        data = DashboardService().get_dashboard_data()

        self.assertIsNotNone(data.replay_data)
        self.assertEqual(data.replay_data.total_candles, 0)
        self.assertIsNone(data.replay_data.current_candle)

    def test_estrategias_carregam_corretamente(self) -> None:
        """Aba Estrategias deve expor contagem do sistema."""
        data = DashboardService().get_dashboard_data()

        self.assertGreaterEqual(data.system_status.loaded_strategies_count, 0)

    def test_research_lab_carrega_corretamente(self) -> None:
        """Research Lab deve expor listas e status seguros."""
        data = DashboardService().get_dashboard_data()

        self.assertIsInstance(data.research_lab_experiments, list)
        self.assertIsInstance(data.research_benchmarks, list)
        self.assertIsInstance(data.parameter_grid_results, list)
        self.assertIsInstance(data.benchmark_validations, list)
        self.assertIsInstance(data.available_research_strategies, list)
        self.assertIsNotNone(data.alpha001_status)
        self.assertIsNotNone(data.alpha001_research_report)

    def test_eventos_carregam_corretamente(self) -> None:
        """Aba Eventos deve expor contagem de eventos."""
        data = DashboardService().get_dashboard_data()

        self.assertGreaterEqual(data.system_status.event_count, 0)

    def test_sistema_carrega_corretamente(self) -> None:
        """Sistema deve expor configuracao e sessao operacional."""
        data = DashboardService().get_dashboard_data()

        self.assertIsNotNone(data.configuration_data)
        self.assertIsNotNone(data.session_snapshot)
        self.assertTrue(data.configuration_data.symbol)

    def test_dashboard_service_nao_lanca_excecoes(self) -> None:
        """Consulta geral da fachada deve ser segura."""
        data = DashboardService().get_dashboard_data()

        self.assertIsInstance(data, DashboardData)


if __name__ == "__main__":
    unittest.main()
