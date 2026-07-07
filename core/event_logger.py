"""Logger em memoria para eventos internos."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class LoggedEvent:
    """Evento registrado pelo logger."""

    event_name: str
    payload: Any
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"),
        compare=False,
    )


@dataclass
class EventLogger:
    """Registra eventos publicados no EventBus em memoria."""

    events: list[LoggedEvent] = field(default_factory=list)

    def handle_event(self, event_name: str, payload: Any) -> None:
        """Registra um evento recebido."""
        self.events.append(LoggedEvent(event_name, payload))

    def get_events(self) -> list[LoggedEvent]:
        """Retorna uma copia dos eventos registrados."""
        return list(self.events)

    def clear(self) -> None:
        """Remove todos os eventos registrados."""
        self.events.clear()
