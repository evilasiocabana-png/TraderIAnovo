"""Contrato oficial do ciclo de vida de uma Alpha."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping


class AlphaLifecycleStatus(Enum):
    """Estados institucionais do ciclo de vida de uma Alpha."""

    HYPOTHESIS = "HYPOTHESIS"
    PLAYBOOK = "PLAYBOOK"
    IMPLEMENTATION = "IMPLEMENTATION"
    RESEARCH = "RESEARCH"
    VALIDATION = "VALIDATION"
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class AlphaLifecycle:
    """Representa exclusivamente o estado do ciclo de vida de uma Alpha."""

    alpha_id: str
    current_status: AlphaLifecycleStatus
    previous_status: AlphaLifecycleStatus | None
    created_at: datetime
    updated_at: datetime
    metadata: Mapping[str, object]
