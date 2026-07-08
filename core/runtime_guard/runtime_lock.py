"""Lock Runtime Guard compatibilidade sobre RuntimeLockService legado."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.runtime_lock_service import RuntimeLockResult, RuntimeLockService


@dataclass
class RuntimeGuardLock:
    """Fachada de lock para impedir ciclos concorrentes."""

    app_name: str = "TraderIA Novo"
    lock_path: Path | None = None
    stale_after_seconds: float | None = None
    _service: RuntimeLockService = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._service = RuntimeLockService(
            app_name=self.app_name,
            lock_path=self.lock_path,
            stale_after_seconds=self.stale_after_seconds,
        )

    def acquire_active(self, *, mode: str = "ACTIVE") -> RuntimeLockResult:
        return self._service.acquire_active(mode=mode)

    def release_if_owned(self) -> None:
        self._service.release_if_owned()
