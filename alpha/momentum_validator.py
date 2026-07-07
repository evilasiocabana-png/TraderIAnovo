"""Validador de momentum para a Alpha 001 IORB."""

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class MomentumResult:
    """Resultado da validacao de momentum apos rompimento."""

    approved: bool
    direction: str
    strength: float
    reason: str


@dataclass(frozen=True)
class MomentumValidator:
    """Valida momentum sem detectar rompimento ou executar ordens."""

    def validate(
        self,
        candles: Sequence[Any],
        breakout_direction: str,
    ) -> MomentumResult:
        """Valida se os dois ultimos candles confirmam a direcao."""
        direction = breakout_direction.upper()
        if len(candles) < 2:
            return self._rejected("WAIT", 0.0, "candles insuficientes")

        if direction == "WAIT":
            return self._rejected("WAIT", 0.0, "sem rompimento para validar")

        previous_close = float(candles[-2].fechamento)
        current_close = float(candles[-1].fechamento)

        if direction == "BUY":
            return self._validate_buy(previous_close, current_close)
        if direction == "SELL":
            return self._validate_sell(previous_close, current_close)

        return self._rejected("WAIT", 0.0, "sem rompimento para validar")

    def _validate_buy(
        self,
        previous_close: float,
        current_close: float,
    ) -> MomentumResult:
        strength = current_close - previous_close
        if strength > 0:
            return MomentumResult(True, "BUY", strength, "momentum comprador")
        return self._rejected("BUY", 0.0, "sem momentum comprador")

    def _validate_sell(
        self,
        previous_close: float,
        current_close: float,
    ) -> MomentumResult:
        strength = previous_close - current_close
        if strength > 0:
            return MomentumResult(True, "SELL", strength, "momentum vendedor")
        return self._rejected("SELL", 0.0, "sem momentum vendedor")

    def _rejected(
        self,
        direction: str,
        strength: float,
        reason: str,
    ) -> MomentumResult:
        return MomentumResult(
            approved=False,
            direction=direction,
            strength=strength,
            reason=reason,
        )
