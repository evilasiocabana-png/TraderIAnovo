"""Registro de ciclos em segundo plano que sobrevive aos reruns do Streamlit."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


_LOCK = threading.Lock()
_THREADS: dict[str, threading.Thread] = {}
_SNAPSHOTS: dict[str, Any] = {}


def start_background_runtime_once(name: str, target: Callable[[], None]) -> bool:
    """Inicia um daemon apenas quando nao existe outro vivo com o mesmo nome."""
    with _LOCK:
        current = _THREADS.get(name)
        if current is not None and current.is_alive():
            return False

        def run_registered_target() -> None:
            try:
                target()
            finally:
                with _LOCK:
                    registered = _THREADS.get(name)
                    if registered is threading.current_thread():
                        _THREADS.pop(name, None)

        thread = threading.Thread(
            target=run_registered_target,
            name=name,
            daemon=True,
        )
        _THREADS[name] = thread
        thread.start()
        return True


def is_background_runtime_running(name: str) -> bool:
    """Informa se o ciclo nomeado continua ativo neste processo."""
    with _LOCK:
        thread = _THREADS.get(name)
        return bool(thread is not None and thread.is_alive())


def publish_background_snapshot(key: str, value: Any) -> None:
    """Publica o ultimo resultado imutavel para todas as sessoes Streamlit."""
    with _LOCK:
        _SNAPSHOTS[str(key)] = value


def get_background_snapshot(key: str, default: Any = None) -> Any:
    """Le o snapshot process-local sem disparar um novo ciclo externo."""
    with _LOCK:
        return _SNAPSHOTS.get(str(key), default)


def clear_background_snapshot(key: str) -> None:
    """Remove apenas o snapshot indicado, preservando threads registradas."""
    with _LOCK:
        _SNAPSHOTS.pop(str(key), None)
