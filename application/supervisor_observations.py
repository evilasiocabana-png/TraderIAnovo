"""Passive telemetry. Never queries MT5, waits for I/O, or changes a decision."""
import json
import os
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_queue = queue.Queue(maxsize=8)
_thread = None
_lock = threading.Lock()
_last = {}


def _write():
    from application.system_supervisor import atomic_json
    while True:
        kind, payload, stamp = _queue.get()
        try:
            atomic_json(ROOT / '.traderia/runtime/supervisor_observations' / (kind + '.json'),
                        dict(observed_at=stamp, payload=payload))
        except Exception:
            # Missing/stale evidence is PENDING, never a fabricated success.
            pass
        finally:
            _queue.task_done()


def publish(kind, payload):
    """Bounded, best-effort enqueue. Dropped telemetry never delays an order."""
    global _thread
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return
    if kind == 'm29_sequence' and not (isinstance(payload.get('account'), dict) and payload['account'].get('login')):
        return
    if kind not in {'m29_sequence', 'forex_batch'}:
        return
    now = time.monotonic()
    if now - _last.get(kind, -1000) < 30:
        return
    if not _lock.acquire(blocking=False):
        return
    try:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_write, daemon=True, name='supervisor-telemetry')
            _thread.start()
        _queue.put_nowait((kind, payload, datetime.now(timezone.utc).isoformat()))
        _last[kind] = now
    except Exception:
        pass
    finally:
        _lock.release()
