"""Shared coordination for lightweight MT5 subprocess reads."""

from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Any, Iterator


_MT5_EXTERNAL_PROCESS_LOCK = threading.Lock()
_MT5_EXTERNAL_CACHE_LOCK = threading.Lock()
_REPORT_STATE_LOCK = threading.Lock()
_REPORT_CANCEL = None
_OPERATIONAL_WAITERS = 0
_MT5_EXTERNAL_CACHE: dict[str, tuple[float, Any]] = {}


@contextmanager
def mt5_external_process_slot(*, timeout: float = 0.0) -> Iterator[bool]:
    """Allow at most one MT5 subprocess from the Streamlit process."""

    wait = max(float(timeout), 0.0)
    global _OPERATIONAL_WAITERS
    with _REPORT_STATE_LOCK:
        _OPERATIONAL_WAITERS += 1
        if _REPORT_CANCEL is not None:
            _REPORT_CANCEL.set()
    try:
        acquired = _MT5_EXTERNAL_PROCESS_LOCK.acquire(timeout=wait)
    finally:
        with _REPORT_STATE_LOCK:
            _OPERATIONAL_WAITERS -= 1
    try:
        yield acquired
    finally:
        if acquired:
            _MT5_EXTERNAL_PROCESS_LOCK.release()


def get_mt5_external_cache(key: str, *, ttl_seconds: float) -> Any | None:
    """Return a fresh shared payload without exposing mutable cache state."""

    with _MT5_EXTERNAL_CACHE_LOCK:
        cached = _MT5_EXTERNAL_CACHE.get(str(key))
        if cached is None or time.monotonic() - cached[0] > max(ttl_seconds, 0.0):
            return None
        value = cached[1]
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, list):
            return list(value)
        return value


def set_mt5_external_cache(key: str, value: Any) -> None:
    """Publish a compact read result for other MT5 adapters in this process."""

    with _MT5_EXTERNAL_CACHE_LOCK:
        _MT5_EXTERNAL_CACHE[str(key)] = (time.monotonic(), value)



@contextmanager
def mt5_report_process_slot(*, timeout=0.0):
    """Read-only reports yield the shared slot to operational reads."""
    global _REPORT_CANCEL
    cancel = None
    # Report requests never queue ahead of operations or an existing report.
    with _REPORT_STATE_LOCK:
        if not _OPERATIONAL_WAITERS and _MT5_EXTERNAL_PROCESS_LOCK.acquire(blocking=False):
            cancel = threading.Event()
            _REPORT_CANCEL = cancel
    try:
        yield cancel
    finally:
        if cancel is not None:
            with _REPORT_STATE_LOCK:
                _REPORT_CANCEL = None
                _MT5_EXTERNAL_PROCESS_LOCK.release()
