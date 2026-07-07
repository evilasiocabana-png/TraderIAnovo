"""Historico de candles em memoria."""

from dataclasses import dataclass, field

from domain.candle import Candle


@dataclass
class CandleHistory:
    """Armazena candles recentes respeitando um limite maximo."""

    max_size: int = 500
    candles: list[Candle] = field(default_factory=list)

    def add_candle(self, candle: Candle) -> None:
        """Adiciona um candle e remove o mais antigo se necessario."""
        self.candles.append(candle)
        self._trim()

    def last(self) -> Candle | None:
        """Retorna o ultimo candle."""
        if not self.candles:
            return None
        return self.candles[-1]

    def previous(self) -> Candle | None:
        """Retorna o candle anterior ao ultimo."""
        if len(self.candles) < 2:
            return None
        return self.candles[-2]

    def last_n(self, n: int) -> list[Candle]:
        """Retorna os ultimos N candles."""
        if n <= 0:
            return []
        return self.candles[-n:]

    def count(self) -> int:
        """Retorna a quantidade de candles armazenados."""
        return len(self.candles)

    def clear(self) -> None:
        """Remove todos os candles do historico."""
        self.candles.clear()

    def _trim(self) -> None:
        overflow = len(self.candles) - self.max_size
        if overflow > 0:
            del self.candles[:overflow]
