"""Adaptador Parquet para a porta de dados historicos."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.candle import Candle
from market_data.adapters import HistoricalDataAdapter
from market_data.historical_data_source import (
    HistoricalDataSourceResult,
)


@dataclass
class ParquetHistoricalDataAdapter(HistoricalDataAdapter):
    """Le candles historicos a partir de uma origem Parquet."""

    supported_formats = ("parquet",)
    adapter_label = "parquet"
    errors: list[str] = field(default_factory=list)

    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega Parquet e retorna candles ou erros normalizados."""
        self.errors.clear()
        try:
            rows = self._read_rows(source)
        except ImportError:
            return self._error("Dependencia para leitura Parquet indisponivel.")
        except (FileNotFoundError, IsADirectoryError, OSError, ValueError) as exc:
            return self._error(f"Arquivo Parquet invalido: {exc}")
        if not rows:
            return self._error("Parquet sem dados.")
        candles = self._candles(rows)
        if self.errors:
            return HistoricalDataSourceResult(candles=[], errors=list(self.errors))
        return HistoricalDataSourceResult(candles=candles, errors=[])

    def _read_rows(self, source: Any) -> list[dict[str, object]]:
        import pandas as pd

        path = Path(source)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("arquivo inexistente.")
        frame = pd.read_parquet(path)
        if frame.empty:
            return []
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        rows = frame.to_dict(orient="records")
        return [self._normalize_row(row) for row in rows]

    def _candles(self, rows: list[dict[str, object]]) -> list[Candle]:
        candles: list[Candle] = []
        if not self._has_required_values(rows[0]):
            self.errors.append("Parquet com estrutura invalida.")
            return candles
        for index, row in enumerate(rows, start=1):
            if not self._row_complete(row):
                self.errors.append(f"Candle incompleto no registro {index}.")
                continue
            self._append_candle(row, index, candles)
        return candles

    def _append_candle(
        self,
        row: dict[str, object],
        index: int,
        candles: list[Candle],
    ) -> None:
        timestamp = self._timestamp(row["datetime"])
        if timestamp is None:
            self.errors.append(f"Timestamp invalido no registro {index}.")
            return
        try:
            candle = Candle(
                data=timestamp,
                abertura=float(row["open"]),
                maxima=float(row["high"]),
                minima=float(row["low"]),
                fechamento=float(row["close"]),
                volume=int(float(row["volume"])),
            )
        except (TypeError, ValueError):
            self.errors.append(f"Candle invalido no registro {index}.")
            return
        if not self._ohlc_is_valid(candle):
            self.errors.append(f"OHLC invalido no registro {index}.")
            return
        candles.append(candle)

    def _normalize_row(self, row: dict[str, object]) -> dict[str, object]:
        normalized = self._empty_normalized_row()
        lower_row = {
            str(key).strip().lower(): value
            for key, value in row.items()
            if key is not None
        }
        for canonical, aliases in self._aliases().items():
            normalized[canonical] = self._first_available(lower_row, aliases)
        return normalized

    def _first_available(
        self,
        row: dict[str, object],
        aliases: tuple[str, ...],
    ) -> object:
        for alias in aliases:
            if alias in row:
                return row[alias]
        return None

    def _has_required_values(self, row: dict[str, object]) -> bool:
        if not all(column in row for column in self._required_columns()):
            return False
        return not all(
            self._is_missing(row.get(column))
            for column in self._required_columns()
        )

    def _row_complete(self, row: dict[str, object]) -> bool:
        return all(not self._is_missing(row.get(column)) for column in self._required_columns())

    def _timestamp(self, value: object) -> str | None:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        return None

    def _ohlc_is_valid(self, candle: Candle) -> bool:
        return (
            candle.maxima >= candle.minima
            and candle.maxima >= candle.abertura
            and candle.maxima >= candle.fechamento
            and candle.minima <= candle.abertura
            and candle.minima <= candle.fechamento
            and candle.volume >= 0
        )

    def _is_missing(self, value: object) -> bool:
        if value is None:
            return True
        return str(value).strip().lower() in {"", "nan", "nat"}

    def _empty_normalized_row(self) -> dict[str, object]:
        return {column: None for column in self._required_columns()}

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

    def _error(self, message: str) -> HistoricalDataSourceResult:
        self.errors.append(message)
        return HistoricalDataSourceResult(candles=[], errors=list(self.errors))
