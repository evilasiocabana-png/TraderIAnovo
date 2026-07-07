"""Detector de rompimento para a Alpha 001 IORB."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BreakoutResult:
    """Resultado da avaliacao de rompimento da Opening Range."""

    direction: str
    breakout: bool
    breakout_price: float | None
    reason: str


@dataclass(frozen=True)
class BreakoutDetector:
    """Detecta rompimento sem calcular faixa ou executar ordens."""

    def detect(self, opening_range: Any, current_price: float) -> BreakoutResult:
        """Classifica o preco atual em BUY, SELL ou WAIT."""
        if not getattr(opening_range, "is_complete", False):
            return BreakoutResult(
                direction="WAIT",
                breakout=False,
                breakout_price=None,
                reason="opening range incompleta",
            )

        high = getattr(opening_range, "high", None)
        low = getattr(opening_range, "low", None)

        if current_price > high:
            return self._breakout("BUY", current_price, "rompimento da maxima")
        if current_price < low:
            return self._breakout("SELL", current_price, "rompimento da minima")

        return BreakoutResult(
            direction="WAIT",
            breakout=False,
            breakout_price=None,
            reason="preco dentro da opening range",
        )

    def _breakout(
        self,
        direction: str,
        current_price: float,
        reason: str,
    ) -> BreakoutResult:
        return BreakoutResult(
            direction=direction,
            breakout=True,
            breakout_price=current_price,
            reason=reason,
        )
