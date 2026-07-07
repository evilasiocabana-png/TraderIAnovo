"""Testes da sessao operacional em memoria."""

import unittest

from core.operation_session import OperationSession


class OperationSessionTest(unittest.TestCase):
    """Valida o estado de sessao operacional."""

    def test_register_operation_incrementa_total(self) -> None:
        """Garante incremento de operacoes do dia."""
        session = self._session()

        session.register_operation()

        self.assertEqual(session.operations_today, 1)

    def test_register_win_atualiza_lucro(self) -> None:
        """Garante registro de ganho."""
        session = self._session()

        session.register_win(120.0)

        self.assertEqual(session.wins_today, 1)
        self.assertEqual(session.gross_profit, 120.0)
        self.assertEqual(session.net_profit, 120.0)

    def test_register_loss_atualiza_prejuizo(self) -> None:
        """Garante registro de perda."""
        session = self._session()

        session.register_loss(-80.0)

        self.assertEqual(session.losses_today, 1)
        self.assertEqual(session.gross_loss, 80.0)
        self.assertEqual(session.net_profit, -80.0)

    def test_updates_guardam_estado_recente(self) -> None:
        """Garante atualizacao de posicao, sinal e evento."""
        session = self._session()

        session.update_position("comprado")
        session.update_last_signal("BUY")
        session.update_last_event("ORDER_CREATED")

        self.assertEqual(session.current_position, "comprado")
        self.assertEqual(session.last_signal, "BUY")
        self.assertEqual(session.last_event, "ORDER_CREATED")

    def test_reset_session_limpa_estado_mutavel(self) -> None:
        """Garante reset dos dados operacionais."""
        session = self._session()
        session.register_operation()
        session.register_win(50.0)
        session.update_position("comprado")

        session.reset_session()

        self.assertEqual(session.operations_today, 0)
        self.assertEqual(session.net_profit, 0.0)
        self.assertIsNone(session.current_position)

    def _session(self) -> OperationSession:
        return OperationSession(
            session_date="2026-06-25",
            market_open_time="09:00",
            market_close_time="18:00",
        )


if __name__ == "__main__":
    unittest.main()
