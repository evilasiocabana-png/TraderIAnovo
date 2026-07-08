"""Fila/deduplicador leve para leituras MT5."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Hashable


@dataclass(frozen=True)
class MT5RuntimeQueueDecision:
    accepted: bool
    reason: str
    key: Hashable


@dataclass
class MT5RuntimeQueue:
    """Deduplica leituras identicas por TTL."""

    ttl_seconds: float = 5.0
    _last_requests: dict[Hashable, float] = field(default_factory=dict)

    def request(self, key: Hashable, *, now: float | None = None) -> MT5RuntimeQueueDecision:
        current = monotonic() if now is None else float(now)
        last = self._last_requests.get(key)
        if last is not None and current - last < self.ttl_seconds:
            return MT5RuntimeQueueDecision(False, "DEDUPLICATED", key)
        self._last_requests[key] = current
        return MT5RuntimeQueueDecision(True, "ACCEPTED", key)

    def clear_expired(self, *, now: float | None = None) -> list[Any]:
        current = monotonic() if now is None else float(now)
        expired = [
            key for key, timestamp in self._last_requests.items()
            if current - timestamp >= self.ttl_seconds
        ]
        for key in expired:
            self._last_requests.pop(key, None)
        return expired
