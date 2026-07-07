"""Contrato oficial de regra de validacao quantitativa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ValidationRule:
    """Representa uma regra declarativa de validacao quantitativa."""

    rule_id: str
    name: str
    description: str
    severity: str
    threshold: float
    enabled: bool
    metadata: Mapping[str, object]
