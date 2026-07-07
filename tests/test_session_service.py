"""Testes do servico de aplicacao da sessao operacional."""

import unittest

from application.session_service import (
    SessionService,
    SessionSnapshot,
    empty_session_snapshot,
)
from core.operation_session import OperationSession


class SessionServiceTest(unittest.TestCase):
    """Valida exposicao da OperationSession para apresentacao."""

    def test_retorna_snapshot_da_sessao(self) -> None:
        """Garante mapeamento dos campos da sessao."""
        session = OperationSession("2026-06-25", "09:00", "18:00")
        session.register_operation()
        session.register_win(100.0)
        session.update_position("comprado")
        session.update_last_signal("BUY")
        session.update_last_event("ORDER_CREATED")

        snapshot = SessionService(session).get_session_snapshot()

        self.assertIsInstance(snapshot, SessionSnapshot)
        self.assertEqual(snapshot.session_date, "2026-06-25")
        self.assertEqual(snapshot.operations_today, 1)
        self.assertEqual(snapshot.gross_profit, 100.0)
        self.assertEqual(snapshot.current_position, "comprado")
        self.assertEqual(snapshot.last_signal, "BUY")
        self.assertEqual(snapshot.last_event, "ORDER_CREATED")

    def test_empty_session_snapshot_retorna_fallback(self) -> None:
        """Garante fallback amigavel quando nao ha sessao."""
        snapshot = empty_session_snapshot()

        self.assertEqual(snapshot.session_date, "N/D")
        self.assertEqual(snapshot.operations_today, 0)
        self.assertIsNone(snapshot.current_position)


if __name__ == "__main__":
    unittest.main()
