"""Barramento simples de eventos internos."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventBus:
    """Publica eventos para handlers registrados."""

    handlers: dict[str, list[Callable[[Any], None]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def subscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        """Registra um handler para um evento."""
        self.handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        """Remove um handler registrado para um evento."""
        if handler not in self.handlers[event_name]:
            return

        self.handlers[event_name].remove(handler)

    def publish(self, event_name: str, payload: Any) -> None:
        """Publica um evento para todos os handlers."""
        for handler in list(self.handlers[event_name]):
            handler(payload)
