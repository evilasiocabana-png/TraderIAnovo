"""Testes do lock operacional de runtime TraderIA."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
import unittest

from core.runtime_lock_service import RuntimeLockService


class RuntimeLockServiceTest(unittest.TestCase):
    def test_lock_ativo_de_outro_pid_bloqueia_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "runtime_lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "app_name": "TraderIA Novo",
                        "pid": os.getpid() + 10000,
                        "mode": "ACTIVE",
                        "heartbeat_at": datetime.now(UTC).isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            service = RuntimeLockService(lock_path=lock_path, stale_after_seconds=90)
            service._pid_alive = lambda pid: True  # type: ignore[method-assign]

            result = service.acquire_active()

            self.assertFalse(result.acquired)
            self.assertIn("Outro runtime", result.message)

    def test_lock_orfao_e_removido_e_runtime_assume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "runtime_lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "app_name": "TraderIA Novo",
                        "pid": os.getpid() + 10000,
                        "mode": "ACTIVE",
                        "heartbeat_at": datetime.now(UTC).isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            service = RuntimeLockService(lock_path=lock_path, stale_after_seconds=90)
            service._pid_alive = lambda pid: False  # type: ignore[method-assign]

            result = service.acquire_active()

            self.assertTrue(result.acquired)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["pid"], os.getpid())


if __name__ == "__main__":
    unittest.main()
