"""Pipeline oficial do Context Lab."""

from dataclasses import dataclass, field
from typing import Any, Mapping

from market.context.context_quality_engine import ContextQualityEngine
from market.context.market_context import MarketContext
from market.context.market_context_builder import MarketContextBuilder


@dataclass(frozen=True)
class ContextPipeline:
    """Orquestra a montagem e avaliacao do contexto de mercado."""

    context_builder: MarketContextBuilder = field(default_factory=MarketContextBuilder)
    quality_engine: ContextQualityEngine = field(default_factory=ContextQualityEngine)

    def execute(
        self,
        timestamp: str,
        feature_snapshot: Any,
        regime_analysis: Any,
        market_dna: Mapping[str, object],
        liquidity: float,
        session: str,
        metadata: Mapping[str, object],
        previous_contexts: tuple[MarketContext, ...] = (),
    ) -> MarketContext:
        """Executa o fluxo oficial sem recalcular componentes de mercado."""
        context = self.context_builder.build(
            timestamp=timestamp,
            feature_snapshot=feature_snapshot,
            regime_analysis=regime_analysis,
            market_dna=market_dna,
            liquidity=liquidity,
            session=session,
            metadata=metadata,
        )
        self.quality_engine.evaluate(previous_contexts + (context,))
        return context
