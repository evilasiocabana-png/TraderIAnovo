"""Politica unica de ativacao dos modelos operacionais TraderIA."""

from __future__ import annotations

import re


ACTIVE_OPERATIONAL_MODEL_NUMBERS = frozenset(range(1, 8))
RETIRED_OPERATIONAL_MODEL_NUMBERS = frozenset(range(8, 23))


def operational_model_number(value: object) -> int | None:
    """Extrai M1..M22 de IDs canonicos, aliases e comentarios de auditoria."""
    normalized = str(value or "").strip().upper()
    match = re.search(r"(?:MODELO[_ ]?|(?:^|[\s|])M)(\d{1,2})(?:_|\b|$)", normalized)
    if match is None:
        return None
    number = int(match.group(1))
    return number if 1 <= number <= 22 else None


def is_active_operational_model(value: object) -> bool:
    """Retorna True somente para os modelos autorizados a abrir novas ordens."""
    return operational_model_number(value) in ACTIVE_OPERATIONAL_MODEL_NUMBERS


def is_retired_operational_model(value: object) -> bool:
    """Retorna True para M8..M22, preservados apenas para historico/gestao."""
    return operational_model_number(value) in RETIRED_OPERATIONAL_MODEL_NUMBERS
