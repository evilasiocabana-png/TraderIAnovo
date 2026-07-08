"""Guarda leve para evitar runtimes operacionais duplicados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class RuntimeLockResult:
    acquired: bool
    message: str
    lock_path: Path


@dataclass
class RuntimeLockService:
    """Controla um lock de runtime ativo por repositorio.

    O lock protege leituras/rotinas MT5 pesadas contra dois Streamlit abertos
    ao mesmo tempo. Locks antigos ou de PID morto sao removidos.
    """

    app_name: str = "TraderIA Novo"
    lock_path: Path | None = None
    stale_after_seconds: float | None = None

    def acquire_active(self, *, mode: str = "ACTIVE") -> RuntimeLockResult:
        lock_path = self._resolved_lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()
        existing = self._read_lock(lock_path)
        if existing:
            existing_pid = int(existing.get("pid") or 0)
            existing_mode = str(existing.get("mode") or "")
            same_process = existing_pid == current_pid
            if (
                existing_mode == "ACTIVE"
                and not same_process
                and self._pid_alive(existing_pid)
                and not self._is_stale(existing)
            ):
                return RuntimeLockResult(
                    acquired=False,
                    message=(
                        "Outro runtime TraderIA ACTIVE esta usando MT5 "
                        f"(pid={existing_pid})."
                    ),
                    lock_path=lock_path,
                )
            if existing_pid and not same_process and not self._pid_alive(existing_pid):
                self._remove_lock(lock_path)
            elif self._is_stale(existing):
                self._remove_lock(lock_path)

        payload = {
            "app_name": self.app_name,
            "pid": current_pid,
            "cwd": str(Path.cwd()),
            "mode": mode,
            "heartbeat_at": self._now(),
            "started_at": existing.get("started_at") if existing else self._now(),
        }
        lock_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return RuntimeLockResult(
            acquired=True,
            message="Runtime ACTIVE autorizado.",
            lock_path=lock_path,
        )

    def release_if_owned(self) -> None:
        lock_path = self._resolved_lock_path()
        existing = self._read_lock(lock_path)
        if int(existing.get("pid") or 0) == os.getpid():
            self._remove_lock(lock_path)

    def _resolved_lock_path(self) -> Path:
        if self.lock_path is not None:
            return self.lock_path
        root = Path(__file__).resolve().parents[1]
        return root / ".traderia" / "runtime" / "runtime_lock.json"

    def _read_lock(self, lock_path: Path) -> dict[str, object]:
        if not lock_path.exists():
            return {}
        try:
            return json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._remove_lock(lock_path)
            return {}

    def _remove_lock(self, lock_path: Path) -> None:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _is_stale(self, payload: dict[str, object]) -> bool:
        heartbeat = str(payload.get("heartbeat_at") or "")
        try:
            updated = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
        except ValueError:
            return True
        age = (datetime.now(UTC) - updated.astimezone(UTC)).total_seconds()
        return age > self._stale_after_seconds()

    def _stale_after_seconds(self) -> float:
        if self.stale_after_seconds is not None:
            return float(self.stale_after_seconds)
        return float(os.getenv("TRADERIA_RUNTIME_LOCK_STALE_SECONDS", "90"))

    def _pid_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                completed = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                return False
            return str(pid) in (completed.stdout or "")
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
