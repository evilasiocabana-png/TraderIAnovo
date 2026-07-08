"""Snapshot de saude do Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.runtime_guard.runtime_event_log import RuntimeEvent


@dataclass(frozen=True)
class RuntimeHealthSnapshot:
    mode: str = "LIGHT"
    lock_status: str = "UNKNOWN"
    forex_cycle_status: str = "IDLE"
    report_cycle_status: str = "IDLE"
    demo_robot_cycle_status: str = "IDLE"
    cache_status: str = "UNKNOWN"
    stale_resources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    last_events: tuple[RuntimeEvent, ...] = ()
    render_durations: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "lock_status": self.lock_status,
            "forex_cycle_status": self.forex_cycle_status,
            "report_cycle_status": self.report_cycle_status,
            "demo_robot_cycle_status": self.demo_robot_cycle_status,
            "cache_status": self.cache_status,
            "stale_resources": list(self.stale_resources),
            "warnings": list(self.warnings),
            "last_events": [
                {
                    "name": event.name,
                    "message": event.message,
                    "timestamp": event.timestamp,
                }
                for event in self.last_events
            ],
            "render_durations": dict(self.render_durations),
        }
