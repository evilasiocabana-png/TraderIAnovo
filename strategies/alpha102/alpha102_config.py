"""Configuracao oficial da Alpha102."""

from __future__ import annotations

from dataclasses import dataclass

from core.configuration_manager import ConfigurationManager


@dataclass(frozen=True)
class Alpha102Config:
    """Parametros configuraveis da Alpha102."""

    timeframe: str
    holding_period: str
    stop_points: float
    target_points: float
    minimum_volume: float
    minimum_volatility: float
    minimum_confidence: float
    risk_profile: str
    trend_lookback_periods: int
    minimum_trend_strength: float
    minimum_pullback_depth: float
    maximum_pullback_depth: float
    momentum_confirmation_threshold: float

    @classmethod
    def from_configuration_manager(
        cls,
        *,
        timeframe: str,
        holding_period: str,
        minimum_volume: float,
        minimum_volatility: float,
        risk_profile: str,
        trend_lookback_periods: int,
        minimum_trend_strength: float,
        minimum_pullback_depth: float,
        maximum_pullback_depth: float,
        momentum_confirmation_threshold: float,
        configuration_manager: type[ConfigurationManager] = ConfigurationManager,
    ) -> "Alpha102Config":
        """Cria configuracao reutilizando parametros centrais do sistema."""
        configuration = configuration_manager.get_configuration()
        return cls(
            timeframe=timeframe,
            holding_period=holding_period,
            stop_points=configuration.stop_points,
            target_points=configuration.target_points,
            minimum_volume=minimum_volume,
            minimum_volatility=minimum_volatility,
            minimum_confidence=configuration.minimum_confidence,
            risk_profile=risk_profile,
            trend_lookback_periods=trend_lookback_periods,
            minimum_trend_strength=minimum_trend_strength,
            minimum_pullback_depth=minimum_pullback_depth,
            maximum_pullback_depth=maximum_pullback_depth,
            momentum_confirmation_threshold=momentum_confirmation_threshold,
        )
