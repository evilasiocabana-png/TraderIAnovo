"""Preservacao de snapshots visuais validos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def _default_valid_snapshot(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


@dataclass
class RuntimeStatePreserver:
    """Preserva ultimo valor visual valido quando leitura nova vem vazia."""

    _snapshots: dict[str, Any] = field(default_factory=dict)

    def preserve_or_replace(
        self,
        key: str,
        value: Any,
        *,
        validator: Callable[[Any], bool] | None = None,
    ) -> Any:
        valid = (validator or _default_valid_snapshot)(value)
        if valid:
            self._snapshots[key] = value
            return value
        return self._snapshots.get(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self._snapshots.get(key, default)

    def keys(self) -> list[str]:
        return sorted(self._snapshots)
