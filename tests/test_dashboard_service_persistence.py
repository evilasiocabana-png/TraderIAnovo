"""Testes de persistencia da fachada do dashboard no Streamlit."""

import unittest

import dashboard_app
from application.dashboard_service import DashboardService


class DashboardServicePersistenceTest(unittest.TestCase):
    """Valida que reruns nao recriam os servicos do Replay."""

    def test_dashboard_service_nao_e_recriado_quando_ja_existe(self) -> None:
        """DashboardService existente deve ser reutilizado."""
        first, second = self._get_services_across_rerun()

        self.assertIs(first, second)

    def test_dashboard_importa_service_com_metodo_de_datasets(self) -> None:
        """Import usado pelo dashboard deve expor a fachada atualizada."""
        service = dashboard_app.DashboardService()

        self.assertTrue(hasattr(service, "list_historical_datasets"))
        self.assertTrue(service.list_historical_datasets())

    def test_dashboard_service_has_market_data_methods(self) -> None:
        """Contrato minimo exigido pelo dashboard para Market Data."""
        service = DashboardService()

        self.assertTrue(hasattr(service, "list_historical_datasets"))
        self.assertTrue(hasattr(service, "get_historical_provider_metrics"))
        self.assertIsInstance(service.list_historical_datasets(), list)
        self.assertIsInstance(service.get_historical_provider_metrics(), dict)

    def test_dashboard_service_provider_metrics_retorna_estrutura_segura(
        self,
    ) -> None:
        """Metricas por provider devem ter fallback seguro."""
        metrics = DashboardService().get_historical_provider_metrics()

        expected_metric = {
            "total_datasets": 0,
            "validated_datasets": 0,
            "approved_datasets": 0,
            "rejected_datasets": 0,
            "not_validated_datasets": 0,
            "gate_evaluations": 0,
            "allowed": 0,
            "blocked": 0,
            "last_validation_at": None,
            "last_gate_evaluation_at": None,
        }
        self.assertEqual(metrics["csv"], expected_metric)
        self.assertEqual(metrics["parquet"], expected_metric)
        self.assertEqual(metrics["duckdb"], expected_metric)
        self.assertEqual(metrics["historicaldataprovider"]["total_datasets"], 2)
        self.assertEqual(metrics["historicaldataprovider"]["approved_datasets"], 1)

    def test_dashboard_service_exposes_historical_provider_metrics(self) -> None:
        """Contrato minimo exigido pelo hotfix 001B."""
        service = DashboardService()

        self.assertTrue(hasattr(service, "get_historical_provider_metrics"))
        metrics = service.get_historical_provider_metrics()

        self.assertIsInstance(metrics, dict)
        self.assertIn("csv", metrics)
        self.assertIn("parquet", metrics)
        self.assertIn("duckdb", metrics)

    def test_dashboard_service_provider_metrics_delega_servico_real(
        self,
    ) -> None:
        """Servico real de metricas deve ser preferido quando configurado."""
        class ProviderMetricsService:
            def get_metrics(self) -> dict[str, dict[str, object]]:
                return {"csv": {"total_datasets": 7}}

        service = DashboardService()
        object.__setattr__(
            service,
            "historical_provider_metrics_service",
            ProviderMetricsService(),
        )

        self.assertEqual(
            service.get_historical_provider_metrics(),
            {"csv": {"total_datasets": 7}},
        )

    def test_dashboard_service_provider_metrics_instancia_incompleta(
        self,
    ) -> None:
        """Instancia incompleta deve retornar fallback seguro, nao quebrar."""
        service = object.__new__(DashboardService)

        metrics = service.get_historical_provider_metrics()

        self.assertEqual(list(metrics), ["csv", "parquet", "duckdb"])
        self.assertEqual(metrics["csv"]["total_datasets"], 0)
        self.assertIsNone(metrics["duckdb"]["last_gate_evaluation_at"])

    def test_dashboard_service_import_direto_tem_metodo_de_datasets(self) -> None:
        """Valida exatamente o contrato minimo do hotfix."""
        service = DashboardService()

        self.assertTrue(hasattr(service, "list_historical_datasets"))
        self.assertTrue(service.list_historical_datasets())

    def test_dashboard_service_legado_sem_metodo_e_substituido(self) -> None:
        """Objeto antigo no session_state nao deve quebrar o dashboard."""
        class LegacyDashboardService:
            def get_dashboard_data(self) -> None:
                return None

        original_session_state = dashboard_app.st.session_state
        fake_session_state = {
            "dashboard_service": LegacyDashboardService(),
        }
        dashboard_app.st.session_state = fake_session_state
        try:
            service = dashboard_app.get_dashboard_service()
        finally:
            dashboard_app.st.session_state = original_session_state

        self.assertIsInstance(service, DashboardService)
        self.assertTrue(hasattr(service, "list_historical_datasets"))
        self.assertTrue(hasattr(service, "get_historical_provider_metrics"))
        self.assertTrue(service.list_historical_datasets())

    def test_dashboard_service_legado_sem_metricas_e_substituido(self) -> None:
        """Instancia antiga sem metricas por provider deve ser recriada."""
        class LegacyDashboardService:
            def get_dashboard_data(self) -> None:
                return None

            def list_historical_datasets(self) -> list[object]:
                return []

        original_session_state = dashboard_app.st.session_state
        fake_session_state = {
            "dashboard_service": LegacyDashboardService(),
        }
        dashboard_app.st.session_state = fake_session_state
        try:
            service = dashboard_app.get_dashboard_service()
        finally:
            dashboard_app.st.session_state = original_session_state

        self.assertIsInstance(service, DashboardService)
        self.assertTrue(hasattr(service, "get_historical_provider_metrics"))

    def test_dashboard_service_com_contrato_incompativel_e_substituido(self) -> None:
        """Instancia em session_state com contrato antigo deve ser descartada."""
        class IncompatibleDashboardService(DashboardService):
            def get_dashboard_contract_version(self) -> str:
                return "0.0"

        original_session_state = dashboard_app.st.session_state
        fake_session_state = {
            "dashboard_service": IncompatibleDashboardService(),
        }
        dashboard_app.st.session_state = fake_session_state
        try:
            service = dashboard_app.get_dashboard_service()
        finally:
            dashboard_app.st.session_state = original_session_state

        self.assertIsInstance(service, DashboardService)
        self.assertNotIsInstance(service, IncompatibleDashboardService)
        self.assertEqual(service.get_dashboard_contract_version(), "1.0")

    def test_replay_service_permanece_a_mesma_instancia(self) -> None:
        """ReplayService deve sobreviver ao rerun."""
        first, second = self._get_services_across_rerun()

        self.assertIs(first.replay_service, second.replay_service)

    def test_replay_engine_permanece_a_mesma_instancia(self) -> None:
        """ReplayEngine deve sobreviver ao rerun."""
        first, second = self._get_services_across_rerun()

        self.assertIs(
            first.replay_service.replay_engine,
            second.replay_service.replay_engine,
        )

    def test_candles_permanecem_carregados_apos_rerun(self) -> None:
        """Candles carregados devem permanecer no ReplayEngine."""
        _, second = self._get_services_across_rerun()

        self.assertGreater(
            len(second.replay_service.replay_engine.candles),
            0,
        )

    def test_total_candles_continua_maior_que_zero(self) -> None:
        """ReplayData deve continuar expondo candles apos rerun."""
        _, second = self._get_services_across_rerun()

        replay_data = second.get_dashboard_data().replay_data

        self.assertIsNotNone(replay_data)
        self.assertGreater(replay_data.total_candles, 0)

    def _get_services_across_rerun(
        self,
    ) -> tuple[DashboardService, DashboardService]:
        original_session_state = dashboard_app.st.session_state
        fake_session_state = {}
        dashboard_app.st.session_state = fake_session_state
        try:
            first = dashboard_app.get_dashboard_service()
            first.load_demo_replay_candles()
            second = dashboard_app.get_dashboard_service()
        finally:
            dashboard_app.st.session_state = original_session_state
        return first, second


if __name__ == "__main__":
    unittest.main()
