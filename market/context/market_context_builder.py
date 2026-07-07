"""Builder de contexto consolidado de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from market.context.market_context import MarketContext
from market.feature_engine import FeatureSnapshot
from market.regime_engine import RegimeAnalysis


@dataclass(frozen=True)
class MarketContextBuilder:
    """Monta MarketContext a partir de resultados ja produzidos."""

    def build(
        self,
        timestamp: str,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        market_dna: Mapping[str, object],
        liquidity: float,
        session: str,
        metadata: Mapping[str, object],
    ) -> MarketContext:
        """Consolida o contexto sem executar classificadores ou engines."""
        return MarketContext(
            timestamp=timestamp,
            regime=regime_analysis.regime.value,
            volatility=feature_snapshot.average_range,
            liquidity=liquidity,
            momentum=feature_snapshot.momentum,
            session=session,
            market_dna=market_dna,
            confidence=regime_analysis.confidence,
            metadata=metadata,
        )
