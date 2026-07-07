"""Contrato para fontes concretas de dados historicos."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from domain.candle import Candle


@dataclass(frozen=True)
class HistoricalDataSourceResult:
    """Resultado bruto normalizado por uma fonte historica concreta."""

    candles: list[Candle] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Indica se a fonte retornou candles utilizaveis."""
        return not self.candles


class HistoricalDataSource(ABC):
    """Porta para leitura de candles historicos independente da origem."""

    @abstractmethod
    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega candles historicos de uma origem concreta."""
