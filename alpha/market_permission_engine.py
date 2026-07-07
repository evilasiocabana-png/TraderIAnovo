"""Motor de permissao de mercado para a Alpha 001 IORB."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MarketPermission(Enum):
    """Permissoes possiveis para avaliacao de mercado."""

    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class MarketPermissionResult:
    """Resultado da avaliacao de permissao operacional."""

    permission: MarketPermission
    reasons: list[str]


@dataclass(frozen=True)
class MarketPermissionEngine:
    """Avalia se o mercado permite operacao sem gerar sinais ou ordens."""

    minimum_research_confidence: float = 60.0
    denied_range_regimes: set[str] = field(default_factory=lambda: {"RANGE"})

    def evaluate(
        self,
        feature_snapshot: Any,
        regime_analysis: Any,
        research_data: Any,
    ) -> MarketPermissionResult:
        """Retorna ALLOW ou DENY conforme os filtros iniciais da Alpha 001."""
        reasons = self._deny_reasons(
            feature_snapshot,
            regime_analysis,
            research_data,
        )

        if reasons:
            return MarketPermissionResult(MarketPermission.DENY, reasons)

        return MarketPermissionResult(
            MarketPermission.ALLOW,
            ["Mercado permitido para avaliacao da Alpha 001."],
        )

    def _deny_reasons(
        self,
        feature_snapshot: Any,
        regime_analysis: Any,
        research_data: Any,
    ) -> list[str]:
        reasons: list[str] = []
        if self._regime_name(regime_analysis) in self.denied_range_regimes:
            reasons.append("Regime RANGE nao permite operacao.")
        if getattr(feature_snapshot, "volatility_level", None) == "LOW":
            reasons.append("Volatilidade LOW nao permite operacao.")
        if self._research_confidence(research_data) < self.minimum_research_confidence:
            reasons.append("Research confidence abaixo do minimo.")
        return reasons

    def _regime_name(self, regime_analysis: Any) -> str:
        regime = getattr(regime_analysis, "regime", "")
        return str(getattr(regime, "value", regime)).upper()

    def _research_confidence(self, research_data: Any) -> float:
        return float(getattr(research_data, "confidence", 0.0))
