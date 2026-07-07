"""Configuracao oficial da Alpha201."""

from __future__ import annotations

from dataclasses import dataclass

from core.configuration_manager import ConfigurationManager


@dataclass(frozen=True)
class Alpha201Config:
    """Parametros configuraveis da Alpha201."""

    timeframe: str
    holding_period: str
    stop_points: float
    target_points: float
    minimum_volume: float
    minimum_volatility: float
    minimum_confidence: float
    risk_profile: str

    @classmethod
    def from_configuration_manager(
        cls,
        *,
        timeframe: str,
        holding_period: str,
        minimum_volume: float,
        minimum_volatility: float,
        risk_profile: str,
        configuration_manager: type[ConfigurationManager] = ConfigurationManager,
    ) -> "Alpha201Config":
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
        )
