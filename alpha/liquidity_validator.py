"""Validador de liquidez para a Alpha 001 IORB."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiquidityResult:
    """Resultado da validacao de liquidez da Alpha 001."""

    approved: bool
    current_volume: float
    minimum_volume: float
    reason: str


@dataclass(frozen=True)
class LiquidityValidator:
    """Valida liquidez sem alterar snapshot ou executar ordens."""

    def validate(
        self,
        market_snapshot: Any,
        minimum_volume: float,
    ) -> LiquidityResult:
        """Valida se a liquidez atual atende ao volume minimo exigido."""
        current_volume = self._current_volume(market_snapshot)
        if current_volume is None:
            return LiquidityResult(
                approved=False,
                current_volume=0.0,
                minimum_volume=minimum_volume,
                reason="volume indisponivel",
            )

        if current_volume >= minimum_volume:
            return LiquidityResult(
                approved=True,
                current_volume=current_volume,
                minimum_volume=minimum_volume,
                reason="liquidez suficiente",
            )

        return LiquidityResult(
            approved=False,
            current_volume=current_volume,
            minimum_volume=minimum_volume,
            reason="liquidez insuficiente",
        )

    def _current_volume(self, market_snapshot: Any) -> float | None:
        value = getattr(market_snapshot, "liquidity", None)
        if value is None:
            return None
        return float(value)
