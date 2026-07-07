"""Contrato oficial da suite de validacao cientifica."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ValidationSuiteStep(Enum):
    """Validacoes suportadas pela suite cientifica."""

    WALK_FORWARD = "WALK_FORWARD"
    MONTE_CARLO = "MONTE_CARLO"
    STRESS_TESTING = "STRESS_TESTING"


@dataclass(frozen=True)
class ValidationSuite:
    """Representa um conjunto padronizado de validacoes."""

    suite_id: str
    name: str
    enabled_steps: tuple[ValidationSuiteStep, ...]
    required_steps: tuple[ValidationSuiteStep, ...]
    created_at: str
    metadata: Mapping[str, object]
