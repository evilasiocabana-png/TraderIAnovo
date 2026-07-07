"""Interface oficial para provedores de dados de mercado."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from market_data.historical_dataset import HistoricalDataset


@dataclass
class DataProvider(ABC):
    """Porta oficial para leitura de dados normalizados de mercado."""

    @abstractmethod
    def load(self, *args: Any, **kwargs: Any) -> HistoricalDataset:
        """Carrega dados de mercado e retorna um dataset normalizado."""

    @abstractmethod
    def symbols(self) -> list[str]:
        """Lista simbolos disponiveis no provedor."""

    @abstractmethod
    def available_periods(self) -> list[str]:
        """Lista periodos/timeframes disponiveis no provedor."""
