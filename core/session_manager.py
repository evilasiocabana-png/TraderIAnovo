"""Gerenciador de sessao operacional orientado a eventos."""

from dataclasses import dataclass
from typing import Any

from core.event_bus import EventBus
from core.events import (
    DECISION_CREATED,
    ORDER_CLOSED,
    ORDER_CREATED,
    STRATEGY_SIGNAL_CREATED,
    SYSTEM_STARTED,
)
from core.operation_session import OperationSession


@dataclass(frozen=True)
class SessionManager:
    """Atualiza OperationSession a partir de eventos publicados."""

    event_bus: EventBus
    session: OperationSession

    def subscribe(self) -> None:
        """Inscreve o gerenciador nos eventos da sessao."""
        self.event_bus.subscribe(SYSTEM_STARTED, self._on_system_started)
        self.event_bus.subscribe(STRATEGY_SIGNAL_CREATED, self._on_strategy_signal)
        self.event_bus.subscribe(ORDER_CREATED, self._on_order_created)
        self.event_bus.subscribe(ORDER_CLOSED, self._on_order_closed)
        self.event_bus.subscribe(DECISION_CREATED, self._on_decision_created)

    def _on_system_started(self, payload: Any) -> None:
        self.session.reset_session()
        self.session.update_last_event(SYSTEM_STARTED)

    def _on_strategy_signal(self, payload: Any) -> None:
        self.session.update_last_signal(payload)

    def _on_order_created(self, payload: Any) -> None:
        self.session.register_operation()
        self.session.update_last_event(ORDER_CREATED)

    def _on_order_closed(self, payload: Any) -> None:
        self.session.update_last_event(ORDER_CLOSED)

    def _on_decision_created(self, payload: Any) -> None:
        self.session.update_last_event(DECISION_CREATED)
