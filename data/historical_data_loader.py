"""Importador de candles historicos do WDO em CSV."""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from domain.candle import Candle


@dataclass
class HistoricalDataLoader:
    """Carrega, valida e converte CSV historico em candles."""

    rows: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    headers: set[str] = field(default_factory=set)
    _candles: list[Candle] = field(default_factory=list)

    def load_csv(self, path: str | Path) -> "HistoricalDataLoader":
        """Carrega um CSV historico para validacao posterior."""
        self.rows.clear()
        self.errors.clear()
        self.headers.clear()
        self._candles.clear()
        csv_path = Path(path)
        if not csv_path.exists() or not csv_path.is_file():
            self.errors.append("Arquivo CSV invalido ou inexistente.")
            return self
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                self.errors.append("CSV sem cabecalho.")
                return self
            self.headers = {
                field.strip().lower()
                for field in reader.fieldnames
                if field is not None
            }
            self.rows = [self._normalize_row(row) for row in reader]
        return self

    def validate(self) -> bool:
        """Valida estrutura, timestamps e integridade dos candles."""
        self.errors.clear()
        self._candles.clear()
        if not self.rows:
            self.errors.append("CSV sem dados.")
            return False
        if not self._has_required_columns():
            self.errors.append("CSV com estrutura invalida.")
            return False
        self._validate_rows()
        return not self.errors

    def candles(self) -> list[Candle]:
        """Retorna candles convertidos apos validacao bem-sucedida."""
        if not self._candles and not self.validate():
            return []
        return list(self._candles)

    def _validate_rows(self) -> None:
        for index, row in enumerate(self.rows, start=2):
            if not self._row_complete(row):
                self.errors.append(f"Candle incompleto na linha {index}.")
                continue
            if not self._timestamp_is_valid(row["datetime"]):
                self.errors.append(f"Timestamp invalido na linha {index}.")
                continue
            self._append_candle(row, index)

    def _append_candle(self, row: dict[str, str], index: int) -> None:
        try:
            candle = Candle(
                data=row["datetime"],
                abertura=float(row["open"]),
                maxima=float(row["high"]),
                minima=float(row["low"]),
                fechamento=float(row["close"]),
                volume=int(float(row["volume"])),
            )
        except ValueError:
            self.errors.append(f"Candle invalido na linha {index}.")
            return
        if not self._ohlc_is_valid(candle):
            self.errors.append(f"OHLC invalido na linha {index}.")
            return
        self._candles.append(candle)

    def _normalize_row(self, row: dict[str, str]) -> dict[str, str]:
        normalized = self._empty_normalized_row()
        lower_row = {
            key.strip().lower(): value.strip()
            for key, value in row.items()
            if key is not None and value is not None
        }
        for canonical, aliases in self._aliases().items():
            normalized[canonical] = self._first_available(lower_row, aliases)
        return normalized

    def _first_available(
        self,
        row: dict[str, str],
        aliases: tuple[str, ...],
    ) -> str:
        for alias in aliases:
            if alias in row:
                return row[alias]
        return ""

    def _has_required_columns(self) -> bool:
        aliases = self._aliases()
        for column in self._required_columns():
            if not any(alias in self.headers for alias in aliases[column]):
                return False
        return True

    def _row_complete(self, row: dict[str, str]) -> bool:
        return all(row.get(column, "").strip() for column in self._required_columns())

    def _timestamp_is_valid(self, value: str) -> bool:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False

    def _ohlc_is_valid(self, candle: Candle) -> bool:
        return (
            candle.maxima >= candle.minima
            and candle.maxima >= candle.abertura
            and candle.maxima >= candle.fechamento
            and candle.minima <= candle.abertura
            and candle.minima <= candle.fechamento
            and candle.volume >= 0
        )

    def _empty_normalized_row(self) -> dict[str, str]:
        return {column: "" for column in self._required_columns()}

    def _required_columns(self) -> tuple[str, ...]:
        return ("datetime", "open", "high", "low", "close", "volume")

    def _aliases(self) -> dict[str, tuple[str, ...]]:
        return {
            "datetime": ("datetime", "timestamp", "data", "date", "time"),
            "open": ("open", "abertura", "aberto"),
            "high": ("high", "maxima", "max"),
            "low": ("low", "minima", "min"),
            "close": ("close", "fechamento", "ultimo"),
            "volume": ("volume", "vol"),
        }
