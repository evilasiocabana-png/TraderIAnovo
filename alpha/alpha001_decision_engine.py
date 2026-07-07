"""Orquestrador de decisao da Alpha 001 IORB."""

from dataclasses import dataclass, field
from typing import Any, Sequence

from alpha.alpha001_config import Alpha001Config
from alpha.breakout_detector import BreakoutDetector
from alpha.liquidity_validator import LiquidityValidator
from alpha.momentum_validator import MomentumValidator
from alpha.opening_range_engine import OpeningRangeEngine
from alpha.regime_validator import RegimeValidator
from alpha.volatility_validator import VolatilityValidator


@dataclass(frozen=True)
class Alpha001Decision:
    """Resultado consolidado da avaliacao da Alpha 001."""

    decision: str
    approved: bool
    confidence: float
    reasons: list[str]


@dataclass
class Alpha001DecisionEngine:
    """Coordena componentes Alpha sem duplicar regras internas."""

    config: Alpha001Config = field(default_factory=Alpha001Config)
    opening_range_engine: OpeningRangeEngine = field(
        default_factory=OpeningRangeEngine,
    )
    breakout_detector: BreakoutDetector = field(default_factory=BreakoutDetector)
    momentum_validator: MomentumValidator = field(default_factory=MomentumValidator)
    regime_validator: RegimeValidator = field(default_factory=RegimeValidator)
    volatility_validator: VolatilityValidator = field(
        default_factory=VolatilityValidator,
    )
    liquidity_validator: LiquidityValidator = field(
        default_factory=LiquidityValidator,
    )

    def evaluate(
        self,
        candles: Sequence[Any],
        market_snapshot: Any,
        current_price: float,
        minimum_range_size: float | None = None,
        minimum_volume: float | None = None,
        config: Alpha001Config | None = None,
    ) -> Alpha001Decision:
        """Orquestra a Alpha 001 e retorna BUY, SELL ou WAIT."""
        effective_config = self._effective_config(
            config,
            minimum_range_size,
            minimum_volume,
        )
        opening_range = self.opening_range_engine.build(
            candles,
            start_time=effective_config.opening_range_start_time,
            end_time=effective_config.opening_range_end_time,
        )
        breakout = self.breakout_detector.detect(opening_range, current_price)
        momentum = self.momentum_validator.validate(candles, breakout.direction)
        regime = self.regime_validator.validate(
            market_snapshot,
            effective_config.normalized_allowed_regimes(),
        )
        volatility = self.volatility_validator.validate(
            opening_range,
            effective_config.minimum_range_size,
        )
        liquidity = self.liquidity_validator.validate(
            market_snapshot,
            effective_config.minimum_volume,
        )

        approvals = [
            opening_range.is_complete,
            breakout.breakout,
            momentum.approved,
            regime.approved,
            volatility.approved,
            liquidity.approved,
        ]
        reasons = [
            breakout.reason,
            momentum.reason,
            regime.reason,
            volatility.reason,
            liquidity.reason,
        ]
        approved = all(approvals)
        return Alpha001Decision(
            decision=breakout.direction if approved else "WAIT",
            approved=approved,
            confidence=sum(1 for item in approvals if item) / len(approvals),
            reasons=reasons,
        )

    def _effective_config(
        self,
        config: Alpha001Config | None,
        minimum_range_size: float | None,
        minimum_volume: float | None,
    ) -> Alpha001Config:
        base_config = config or self.config
        return base_config.with_overrides(
            minimum_range_size=minimum_range_size,
            minimum_volume=minimum_volume,
        )
