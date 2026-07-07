"""Contrato para referencia logica de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetReference:
    """DTO imutavel para referencia leve de dataset historico."""

    dataset_id: str
    dataset_name: str
    dataset_version: str
    symbol: str
    timeframe: str
    reference_version: str
