"""Configuracao oficial da Alpha003."""

from __future__ import annotations

from dataclasses import dataclass

from core.configuration_manager import ConfigurationManager


@dataclass(frozen=True)
class Alpha003Config:
    """Parametros configuraveis da Alpha003."""

    session_start: str
    session_end: str
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
        session_start: str,
        session_end: str,
        minimum_volume: float,
        minimum_volatility: float,
        risk_profile: str,
        configuration_manager: type[ConfigurationManager] = ConfigurationManager,
    ) -> "Alpha003Config":
        """Cria configuracao reutilizando parametros centrais do sistema."""
        configuration = configuration_manager.get_configuration()
        return cls(
            session_start=session_start,
            session_end=session_end,
            stop_points=configuration.stop_points,
            target_points=configuration.target_points,
            minimum_volume=minimum_volume,
            minimum_volatility=minimum_volatility,
            minimum_confidence=configuration.minimum_confidence,
            risk_profile=risk_profile,
        )
