"""Testes do barramento oficial de eventos."""

import unittest

from core.event_bus import EventBus
from core.events import DECISION_CREATED, ORDER_CREATED


class EventBusTest(unittest.TestCase):
    """Valida publicacao e assinatura de eventos."""

    def test_um_inscrito_recebe_evento(self) -> None:
        """Garante que um callback inscrito recebe o payload."""
        bus = EventBus()
        recebidos: list[dict[str, str]] = []

        bus.subscribe(DECISION_CREATED, recebidos.append)
        bus.publish(DECISION_CREATED, {"decision": "BUY"})

        self.assertEqual(recebidos, [{"decision": "BUY"}])

    def test_multiplos_inscritos_recebem_evento(self) -> None:
        """Garante entrega para mais de um inscrito."""
        bus = EventBus()
        primeiro: list[str] = []
        segundo: list[str] = []

        bus.subscribe(ORDER_CREATED, primeiro.append)
        bus.subscribe(ORDER_CREATED, segundo.append)
        bus.publish(ORDER_CREATED, "order-1")

        self.assertEqual(primeiro, ["order-1"])
        self.assertEqual(segundo, ["order-1"])

    def test_unsubscribe_funciona_corretamente(self) -> None:
        """Garante que callback removido nao recebe novos eventos."""
        bus = EventBus()
        recebidos: list[str] = []

        bus.subscribe(ORDER_CREATED, recebidos.append)
        bus.unsubscribe(ORDER_CREATED, recebidos.append)
        bus.publish(ORDER_CREATED, "order-1")

        self.assertEqual(recebidos, [])


if __name__ == "__main__":
    unittest.main()
