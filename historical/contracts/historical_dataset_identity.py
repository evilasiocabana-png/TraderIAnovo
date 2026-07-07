"""Contrato para identidade logica de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetIdentity:
    """DTO imutavel para referencia logica estavel de dataset historico."""

    dataset_id: str
    dataset_name: str
    provider_id: str
    source_id: str
    symbol: str
    timeframe: str
    dataset_version: str
    created_at: str
    identity_version: str
