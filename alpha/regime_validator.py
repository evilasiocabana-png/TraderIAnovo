"""Validador de regime de mercado para a Alpha 001 IORB."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RegimeResult:
    """Resultado da validacao de regime da Alpha 001."""

    approved: bool
    regime: str
    reason: str


@dataclass(frozen=True)
class RegimeValidator:
    """Valida se o regime permite avaliacao da estrategia IORB."""

    denied_regime: str = "RANGE"

    def validate(
        self,
        market_snapshot: Any,
        allowed_regimes: tuple[str, ...] = (),
    ) -> RegimeResult:
        """Valida o regime informado pelo MarketSnapshot recebido."""
        regime = self._normalize_regime(getattr(market_snapshot, "regime", None))
        if regime == "UNKNOWN":
            return RegimeResult(False, regime, "regime indisponivel")
        normalized_allowed = tuple(item.strip().upper() for item in allowed_regimes)
        if normalized_allowed and regime not in normalized_allowed:
            return RegimeResult(False, regime, "regime nao permitido")
        if regime == self.denied_regime:
            return RegimeResult(False, regime, "regime desfavoravel")
        return RegimeResult(True, regime, "regime favoravel")

    def _normalize_regime(self, regime: Any) -> str:
        if regime is None:
            return "UNKNOWN"

        normalized = str(getattr(regime, "value", regime)).strip().upper()
        if not normalized:
            return "UNKNOWN"
        return normalized
