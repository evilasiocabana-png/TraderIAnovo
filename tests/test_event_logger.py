"""Testes do logger de eventos em memoria."""

import unittest
from collections.abc import Callable
from typing import Any

from core.event_bus import EventBus
from core.event_logger import EventLogger, LoggedEvent
from core.events import DECISION_CREATED, ORDER_CREATED


class EventLoggerTest(unittest.TestCase):
    """Valida o registro de eventos do EventLogger."""

    def test_registra_um_evento(self) -> None:
        """Garante que um evento recebido fica armazenado."""
        logger = EventLogger()

        logger.handle_event(DECISION_CREATED, {"decision": "BUY"})

        self.assertEqual(
            logger.get_events(),
            [LoggedEvent(DECISION_CREATED, {"decision": "BUY"})],
        )

    def test_registra_multiplos_eventos_conectado_ao_event_bus(self) -> None:
        """Garante funcionamento conectado ao EventBus."""
        bus = EventBus()
        logger = EventLogger()
        bus.subscribe(DECISION_CREATED, self._handler(logger, DECISION_CREATED))
        bus.subscribe(ORDER_CREATED, self._handler(logger, ORDER_CREATED))

        bus.publish(DECISION_CREATED, {"decision": "BUY"})
        bus.publish(ORDER_CREATED, {"order": "order-1"})

        self.assertEqual(len(logger.get_events()), 2)

    def test_limpa_eventos(self) -> None:
        """Garante que clear remove os eventos armazenados."""
        logger = EventLogger()
        logger.handle_event(DECISION_CREATED, {"decision": "BUY"})

        logger.clear()

        self.assertEqual(logger.get_events(), [])

    def _handler(self, logger: EventLogger, event_name: str) -> Callable[[Any], None]:
        return lambda payload: logger.handle_event(event_name, payload)


if __name__ == "__main__":
    unittest.main()
