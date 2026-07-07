"""Porta read-only para provedores de dados de mercado em tempo real."""

from __future__ import annotations

from typing import Any, Protocol

from domain.candle import Candle


class IMarketDataProvider(Protocol):
    """Contrato minimo para adaptadores read-only de candles."""

    def connect(self) -> bool:
        """Inicializa a conexao somente leitura com a fonte externa."""

    def select_symbol(self, symbol: str) -> bool:
        """Seleciona o ativo na fonte externa sem habilitar execucao."""

    def get_candles(self, symbol: str, timeframe: Any, count: int) -> list[Candle]:
        """Retorna candles de dominio e publica os eventos correspondentes."""
