"""Testes das acoes de Replay expostas pelo DashboardService."""

from pathlib import Path
import unittest

from application.dashboard_service import DashboardService
from application.replay_service import ReplayData, ReplayStatus
import dashboard_app
from dashboard_app import replay_control_disabled


class DashboardReplayActionsTest(unittest.TestCase):
    """Valida acoes equivalentes aos botoes do Replay."""

    def test_carregar_demo(self) -> None:
        """Carregar demo deve deixar replay pronto."""
        data = DashboardService().load_demo_replay_candles()

        self.assertIsInstance(data, ReplayData)
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertNotEqual(data.status, ReplayStatus.EMPTY)
        self.assertGreater(data.total_candles, 0)
        self.assertEqual(data.current_index, -1)
        self.assertGreater(len(data.candles_loaded), 0)

    def test_iniciar_replay(self) -> None:
        """Iniciar deve colocar replay em execucao."""
        service = DashboardService()
        service.load_demo_replay_candles()

        data = service.start_replay()

        self.assertEqual(data.status, ReplayStatus.RUNNING)
        self.assertTrue(data.is_running)
        self.assertEqual(data.current_index, 0)

    def test_avancar_proximo_candle(self) -> None:
        """Proximo Candle deve avancar o indice."""
        service = DashboardService()
        service.load_demo_replay_candles()

        first = service.next_replay_candle()
        second = service.next_replay_candle()

        self.assertEqual(first.current_index, 0)
        self.assertEqual(second.current_index, 1)
        self.assertIsNotNone(second.current_candle)

    def test_parar_replay(self) -> None:
        """Parar deve pausar replay em execucao."""
        service = DashboardService()
        service.load_demo_replay_candles()
        service.start_replay()

        data = service.stop_replay()

        self.assertEqual(data.status, ReplayStatus.PAUSED)
        self.assertFalse(data.is_running)

    def test_resetar_replay(self) -> None:
        """Resetar deve voltar para o inicio mantendo candles carregados."""
        service = DashboardService()
        service.load_demo_replay_candles()
        service.next_replay_candle()

        data = service.reset_replay()

        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.current_index, -1)
        self.assertIsNone(data.current_candle)
        self.assertEqual(data.candles_processed, [])

    def test_ativar_auto_replay(self) -> None:
        """Auto replay deve ser ativado pela fachada."""
        service = DashboardService()
        service.load_demo_replay_candles()

        data = service.enable_replay_auto_run(0.5)

        self.assertTrue(data.auto_run_enabled)
        self.assertTrue(service.is_replay_auto_run_enabled())
        self.assertEqual(data.replay_speed_seconds, 0.5)

    def test_desativar_auto_replay(self) -> None:
        """Auto replay deve ser desativado pela fachada."""
        service = DashboardService()
        service.load_demo_replay_candles()
        service.enable_replay_auto_run(0.5)

        data = service.disable_replay_auto_run()

        self.assertFalse(data.auto_run_enabled)
        self.assertFalse(service.is_replay_auto_run_enabled())

    def test_fluxo_completo_dos_botoes_do_replay(self) -> None:
        """Sequencia dos botoes deve funcionar pela fachada."""
        service = DashboardService()

        loaded = service.load_demo_replay_candles()
        started = service.start_replay()
        advanced = service.next_replay_candle()
        stopped = service.stop_replay()
        reset = service.reset_replay()

        self.assertEqual(loaded.status, ReplayStatus.READY)
        self.assertEqual(started.status, ReplayStatus.RUNNING)
        self.assertGreaterEqual(advanced.current_index, 1)
        self.assertEqual(stopped.status, ReplayStatus.PAUSED)
        self.assertEqual(reset.status, ReplayStatus.READY)

    def test_dashboard_atualiza_estado_antes_dos_botoes(self) -> None:
        """Carregar dataset deve atualizar estado antes dos demais botoes."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")
        load_index = source.index("service.load_selected_historical_dataset_to_replay()")
        disabled_index = source.index("replay_control_disabled(replay_data)")

        self.assertIn("service.load_selected_historical_dataset_to_replay()", source)
        self.assertLess(load_index, disabled_index)

    def test_botoes_desabilitados_quando_replay_vazio(self) -> None:
        """Replay vazio deve bloquear acoes que dependem de candles."""
        data = DashboardService().get_dashboard_data().replay_data

        disabled = replay_control_disabled(data)

        self.assertTrue(disabled["start"])
        self.assertTrue(disabled["next"])
        self.assertTrue(disabled["auto"])
        self.assertTrue(disabled["stop"])
        self.assertTrue(disabled["reset"])

    def test_botoes_habilitados_apos_carregar_demo(self) -> None:
        """Replay carregado deve habilitar inicio, proximo e auto replay."""
        data = DashboardService().load_demo_replay_candles()

        disabled = replay_control_disabled(data)

        self.assertFalse(disabled["start"])
        self.assertFalse(disabled["next"])
        self.assertFalse(disabled["auto"])
        self.assertTrue(disabled["stop"])
        self.assertFalse(disabled["reset"])

    def test_botao_parar_habilitado_apenas_rodando(self) -> None:
        """Parar deve ficar disponivel somente durante execucao."""
        service = DashboardService()
        service.load_demo_replay_candles()
        data = service.start_replay()

        disabled = replay_control_disabled(data)

        self.assertFalse(disabled["stop"])

    def test_botoes_bloqueados_quando_replay_finalizado(self) -> None:
        """Replay finalizado deve bloquear novo avanco e auto replay."""
        service = DashboardService()
        service.load_demo_replay_candles()
        data = service.get_dashboard_data().replay_data
        while data is not None and data.status != ReplayStatus.FINISHED:
            data = service.next_replay_candle()

        disabled = replay_control_disabled(data)

        self.assertTrue(disabled["start"])
        self.assertTrue(disabled["next"])
        self.assertTrue(disabled["auto"])
        self.assertTrue(disabled["stop"])
        self.assertFalse(disabled["reset"])

    def test_dashboard_service_reutiliza_instancia_existente(self) -> None:
        """Rerun normal nao deve recriar a fachada do dashboard."""
        original_session_state = dashboard_app.st.session_state
        fake_session_state = {}
        dashboard_app.st.session_state = fake_session_state
        try:
            first = dashboard_app.get_dashboard_service()
            first.load_demo_replay_candles()
            second = dashboard_app.get_dashboard_service()
        finally:
            dashboard_app.st.session_state = original_session_state

        replay_data = second.get_dashboard_data().replay_data
        self.assertIs(first, second)
        self.assertEqual(replay_data.status, ReplayStatus.READY)
        self.assertGreater(replay_data.total_candles, 0)

    def test_dashboard_service_valida_contrato_sem_descartar_instancia_valida(
        self,
    ) -> None:
        """Servico existente e valido em session_state nao deve ser invalidado."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("not _dashboard_service_valido(service)", source)
        self.assertIn("list_historical_datasets", source)
        self.assertIn("callable(getattr(service, method, None))", source)


if __name__ == "__main__":
    unittest.main()
