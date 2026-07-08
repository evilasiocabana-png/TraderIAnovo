"""Fachada de aplicacao para Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, MutableMapping

from core.runtime_guard import (
    MT5RuntimeQueue,
    RuntimeCleanupPolicy,
    RuntimeEventLog,
    RuntimeGuardLock,
    RuntimeHealthSnapshot,
    RuntimeScheduler,
    RuntimeStatePreserver,
)
from core.runtime_guard.runtime_cleanup_policy import RuntimeCleanupResult
from core.runtime_guard.runtime_scheduler import RuntimeScheduleDecision


@dataclass
class RuntimeGuardService:
    """Coordena protecoes de runtime sem decidir operacao."""

    scheduler: RuntimeScheduler = field(default_factory=RuntimeScheduler)
    state_preserver: RuntimeStatePreserver = field(default_factory=RuntimeStatePreserver)
    cleanup_policy: RuntimeCleanupPolicy = field(default_factory=RuntimeCleanupPolicy)
    event_log: RuntimeEventLog = field(default_factory=RuntimeEventLog)
    mt5_queue: MT5RuntimeQueue = field(default_factory=MT5RuntimeQueue)
    runtime_lock: RuntimeGuardLock = field(default_factory=RuntimeGuardLock)

    def preserve_snapshot(
        self,
        key: str,
        value: Any,
        *,
        validator: Callable[[Any], bool] | None = None,
    ) -> Any:
        previous = self.state_preserver.get(key)
        result = self.state_preserver.preserve_or_replace(
            key,
            value,
            validator=validator,
        )
        if result is value and value is not previous:
            self.event_log.record("SNAPSHOT_REPLACED_BY_VALID_READ", key)
        else:
            self.event_log.record("SNAPSHOT_PRESERVED", key)
        return result

    def cleanup_temporary(
        self,
        state: MutableMapping[str, Any],
        *,
        dry_run: bool = False,
    ) -> RuntimeCleanupResult:
        self.event_log.record("RUNTIME_CLEANUP_REQUESTED")
        result = self.cleanup_policy.cleanup_temporary(state, dry_run=dry_run)
        self.event_log.record(
            "RUNTIME_CLEANUP_COMPLETED",
            f"removed={len(result.removed_keys)} dry_run={dry_run}",
        )
        return result

    def cleanup_expired(
        self,
        state: MutableMapping[str, Any],
        timestamps: MutableMapping[str, float],
        *,
        now: float | None = None,
        dry_run: bool = False,
    ) -> RuntimeCleanupResult:
        self.event_log.record("RUNTIME_CLEANUP_REQUESTED", "expired")
        result = self.cleanup_policy.cleanup_expired(
            state,
            timestamps,
            now=now,
            dry_run=dry_run,
        )
        self.event_log.record(
            "RUNTIME_CLEANUP_COMPLETED",
            f"removed={len(result.removed_keys)} dry_run={dry_run}",
        )
        return result

    def should_run_cycle(
        self,
        task_name: str,
        *,
        interval_seconds: float,
        now: float | None = None,
        in_grace_period: bool = False,
        diagnostic_only: bool = False,
    ) -> RuntimeScheduleDecision:
        decision = self.scheduler.should_run(
            task_name,
            interval_seconds=interval_seconds,
            now=now,
            in_grace_period=in_grace_period,
            diagnostic_only=diagnostic_only,
        )
        if decision.allowed:
            self.event_log.record(f"{task_name.upper()}_STARTED")
        else:
            self.event_log.record(
                f"{task_name.upper()}_SKIPPED",
                decision.reason,
            )
        return decision

    def mark_cycle_completed(self, task_name: str, *, now: float | None = None) -> None:
        self.scheduler.mark_run(task_name, now=now)
        self.event_log.record(f"{task_name.upper()}_COMPLETED")

    def request_mt5_read(self, key: object, *, now: float | None = None) -> bool:
        decision = self.mt5_queue.request(key, now=now)
        self.event_log.record("MT5_QUEUE_REQUEST", decision.reason)
        return decision.accepted

    def health_snapshot(
        self,
        *,
        mode: str = "LIGHT",
        lock_status: str = "UNKNOWN",
        forex_cycle_status: str = "IDLE",
        report_cycle_status: str = "IDLE",
        demo_robot_cycle_status: str = "IDLE",
        cache_status: str = "UNKNOWN",
        stale_resources: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        render_durations: dict[str, float] | None = None,
    ) -> RuntimeHealthSnapshot:
        return RuntimeHealthSnapshot(
            mode=mode,
            lock_status=lock_status,
            forex_cycle_status=forex_cycle_status,
            report_cycle_status=report_cycle_status,
            demo_robot_cycle_status=demo_robot_cycle_status,
            cache_status=cache_status,
            stale_resources=stale_resources,
            warnings=warnings,
            last_events=tuple(self.event_log.list_events()[-10:]),
            render_durations=dict(render_durations or {}),
        )
