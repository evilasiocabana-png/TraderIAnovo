"""Validador de volatilidade para a Alpha 001 IORB."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VolatilityResult:
    """Resultado da validacao de volatilidade da Opening Range."""

    approved: bool
    range_size: float
    minimum_required: float
    reason: str


@dataclass(frozen=True)
class VolatilityValidator:
    """Valida volatilidade sem calcular Opening Range ou detectar rompimento."""

    def validate(
        self,
        opening_range: Any,
        minimum_required: float,
    ) -> VolatilityResult:
        """Valida se o tamanho da faixa atende ao minimo exigido."""
        if not getattr(opening_range, "is_complete", False):
            return VolatilityResult(
                approved=False,
                range_size=0.0,
                minimum_required=minimum_required,
                reason="opening range incompleta",
            )

        range_size = float(getattr(opening_range, "range_size", 0.0))
        if range_size >= minimum_required:
            return VolatilityResult(
                approved=True,
                range_size=range_size,
                minimum_required=minimum_required,
                reason="volatilidade suficiente",
            )

        return VolatilityResult(
            approved=False,
            range_size=range_size,
            minimum_required=minimum_required,
            reason="volatilidade insuficiente",
        )
