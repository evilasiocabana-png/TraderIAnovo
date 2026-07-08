"""Log circular de eventos do Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class RuntimeEvent:
    name: str
    message: str = ""
    timestamp: str = ""


@dataclass
class RuntimeEventLog:
    """Armazena ultimos eventos sem crescer indefinidamente."""

    max_size: int = 50
    _events: list[RuntimeEvent] = field(default_factory=list)

    def record(self, name: str, message: str = "") -> RuntimeEvent:
        event = RuntimeEvent(
            name=str(name),
            message=str(message),
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._events.append(event)
        if len(self._events) > self.max_size:
            self._events = self._events[-self.max_size :]
        return event

    def list_events(self) -> list[RuntimeEvent]:
        return list(self._events)

    def as_strings(self) -> list[str]:
        return [
            f"{event.timestamp} {event.name}"
            + (f" {event.message}" if event.message else "")
            for event in self._events
        ]
