"""Configuracao oficial da Alpha002."""

from __future__ import annotations

from dataclasses import dataclass

from core.configuration_manager import ConfigurationManager


@dataclass(frozen=True)
class Alpha002Config:
    """Parametros configuraveis da Alpha002."""

    opening_range: int
    stop_points: float
    target_points: float
    minimum_volume: float
    minimum_volatility: float
    minimum_confidence: float
    session_start: str
    session_end: str

    @classmethod
    def from_configuration_manager(
        cls,
        *,
        opening_range: int,
        minimum_volume: float,
        minimum_volatility: float,
        session_start: str,
        session_end: str,
        configuration_manager: type[ConfigurationManager] = ConfigurationManager,
    ) -> "Alpha002Config":
        """Cria configuracao reutilizando parametros centrais do sistema."""
        configuration = configuration_manager.get_configuration()
        return cls(
            opening_range=opening_range,
            stop_points=configuration.stop_points,
            target_points=configuration.target_points,
            minimum_volume=minimum_volume,
            minimum_volatility=minimum_volatility,
            minimum_confidence=configuration.minimum_confidence,
            session_start=session_start,
            session_end=session_end,
        )
