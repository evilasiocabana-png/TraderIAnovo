"""Scheduler leve para ciclos Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass(frozen=True)
class RuntimeScheduleDecision:
    allowed: bool
    reason: str
    elapsed_seconds: float


@dataclass
class RuntimeScheduler:
    """Controla intervalos sem executar Lab pesado."""

    _last_runs: dict[str, float] = field(default_factory=dict)

    def should_run(
        self,
        task_name: str,
        *,
        interval_seconds: float,
        now: float | None = None,
        in_grace_period: bool = False,
        diagnostic_only: bool = False,
    ) -> RuntimeScheduleDecision:
        current = monotonic() if now is None else float(now)
        if diagnostic_only:
            return RuntimeScheduleDecision(False, "DIAGNOSTIC_ONLY", 0.0)
        if in_grace_period:
            return RuntimeScheduleDecision(False, "UI_GRACE_PERIOD", 0.0)
        last = self._last_runs.get(task_name)
        elapsed = current - last if last is not None else interval_seconds
        if last is not None and elapsed < interval_seconds:
            return RuntimeScheduleDecision(False, "INTERVAL_NOT_REACHED", elapsed)
        return RuntimeScheduleDecision(True, "READY", elapsed)

    def mark_run(self, task_name: str, *, now: float | None = None) -> None:
        self._last_runs[task_name] = monotonic() if now is None else float(now)

    def last_run(self, task_name: str) -> float | None:
        return self._last_runs.get(task_name)
