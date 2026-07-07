"""Perfil oficial de pesquisa de uma Alpha."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaResearchProfile:
    """Contrato imutavel com metadados de pesquisa de uma Alpha."""

    alpha_id: str
    alpha_name: str
    version: int
    description: str
    market: str
    timeframe: str
    status: str
    current_stage: str
    validation_level: str
    configuration_version: int
