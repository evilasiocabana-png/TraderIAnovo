"""Testes do gerenciador de sessao por eventos."""

import unittest

from core.event_bus import EventBus
from core.events import (
    DECISION_CREATED,
    ORDER_CLOSED,
    ORDER_CREATED,
    STRATEGY_SIGNAL_CREATED,
    SYSTEM_STARTED,
)
from core.operation_session import OperationSession
from core.session_manager import SessionManager


class SessionManagerTest(unittest.TestCase):
    """Valida atualizacao da sessao via EventBus."""

    def test_system_started_inicia_nova_sessao(self) -> None:
        """Garante reset da sessao ao iniciar sistema."""
        bus, session = self._manager()
        session.register_operation()

        bus.publish(SYSTEM_STARTED, {})

        self.assertEqual(session.operations_today, 0)
        self.assertEqual(session.last_event, SYSTEM_STARTED)

    def test_strategy_signal_atualiza_ultimo_sinal(self) -> None:
        """Garante atualizacao do ultimo sinal por evento."""
        bus, session = self._manager()

        bus.publish(STRATEGY_SIGNAL_CREATED, "BUY")

        self.assertEqual(session.last_signal, "BUY")

    def test_order_created_incrementa_operacoes_e_evento(self) -> None:
        """Garante incremento quando ordem e criada."""
        bus, session = self._manager()

        bus.publish(ORDER_CREATED, {"order": "1"})

        self.assertEqual(session.operations_today, 1)
        self.assertEqual(session.last_event, ORDER_CREATED)

    def test_decision_created_atualiza_ultimo_evento(self) -> None:
        """Garante atualizacao do evento de decisao."""
        bus, session = self._manager()

        bus.publish(DECISION_CREATED, {"decision": "BUY"})

        self.assertEqual(session.last_event, DECISION_CREATED)

    def test_order_closed_atualiza_ultimo_evento(self) -> None:
        """Garante atualizacao do evento de fechamento."""
        bus, session = self._manager()

        bus.publish(ORDER_CLOSED, {"order": "1"})

        self.assertEqual(session.last_event, ORDER_CLOSED)

    def _manager(self) -> tuple[EventBus, OperationSession]:
        bus = EventBus()
        session = OperationSession("2026-06-25", "09:00", "18:00")
        SessionManager(bus, session).subscribe()
        return bus, session


if __name__ == "__main__":
    unittest.main()
