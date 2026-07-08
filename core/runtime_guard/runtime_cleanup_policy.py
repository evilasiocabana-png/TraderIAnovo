"""Politica de limpeza segura do Runtime Guard."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import MutableMapping, Any

from core.runtime_guard.runtime_state import (
    RuntimeStateCategory,
    classify_runtime_state_key,
)


@dataclass(frozen=True)
class RuntimeCleanupResult:
    removed_keys: tuple[str, ...]
    preserved_keys: tuple[str, ...]
    dry_run: bool = False


@dataclass
class RuntimeCleanupPolicy:
    """Remove somente estado classificado como temporario."""

    max_age_seconds: float = 300.0

    def dry_run_cleanup(self, state: MutableMapping[str, Any]) -> RuntimeCleanupResult:
        return self.cleanup_temporary(state, dry_run=True)

    def cleanup_temporary(
        self,
        state: MutableMapping[str, Any],
        *,
        dry_run: bool = False,
    ) -> RuntimeCleanupResult:
        removed: list[str] = []
        preserved: list[str] = []
        for key in list(state.keys()):
            category = classify_runtime_state_key(str(key))
            if category == RuntimeStateCategory.TEMPORARIO_LIMPAVEL:
                removed.append(str(key))
                if not dry_run:
                    state.pop(key, None)
            else:
                preserved.append(str(key))
        return RuntimeCleanupResult(tuple(removed), tuple(preserved), dry_run)

    def cleanup_expired(
        self,
        state: MutableMapping[str, Any],
        timestamps: MutableMapping[str, float],
        *,
        now: float | None = None,
        dry_run: bool = False,
    ) -> RuntimeCleanupResult:
        current = monotonic() if now is None else float(now)
        removed: list[str] = []
        preserved: list[str] = []
        for key in list(state.keys()):
            category = classify_runtime_state_key(str(key))
            age = current - float(timestamps.get(str(key), current))
            if (
                category == RuntimeStateCategory.TEMPORARIO_LIMPAVEL
                and age >= self.max_age_seconds
            ):
                removed.append(str(key))
                if not dry_run:
                    state.pop(key, None)
            else:
                preserved.append(str(key))
        return RuntimeCleanupResult(tuple(removed), tuple(preserved), dry_run)
