"""Adapter CSV autorizado para dados historicos."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.candle import Candle
from market_data.adapters import HistoricalDataAdapter
from market_data.historical_data_source import HistoricalDataSourceResult


@dataclass
class CsvHistoricalDataAdapter(HistoricalDataAdapter):
    """Contrato formal do adapter CSV historico."""

    supported_formats = ("csv",)
    adapter_label = "csv"
    errors: list[str] = field(default_factory=list)

    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega candles de um arquivo CSV autorizado."""

        self.errors.clear()
        try:
            rows = self._read_rows(source)
        except (FileNotFoundError, IsADirectoryError, OSError) as exc:
            return self._error(f"Arquivo CSV invalido: {exc}")
        if not rows:
            return self._error("CSV sem dados.")
        candles = self._candles(rows)
        if self.errors:
            return HistoricalDataSourceResult(candles=[], errors=list(self.errors))
        return HistoricalDataSourceResult(candles=candles, errors=[])

    def load_candles(self, dataset_ref: Any) -> HistoricalDataSourceResult:
        """Le CSV controlado e retorna candles normalizados."""

        return self.load(dataset_ref)

    def _read_rows(self, source: Any) -> list[dict[str, str]]:
        path = Path(source)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("arquivo inexistente.")
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                self.errors.append("CSV sem cabecalho.")
                return []
            headers = {
                field.strip().lower()
                for field in reader.fieldnames
                if field is not None
            }
            if not self._has_required_columns(headers):
                self.errors.append("CSV sem coluna obrigatoria.")
                return []
            return [self._normalize_row(row) for row in reader]

    def _candles(self, rows: list[dict[str, str]]) -> list[Candle]:
        candles: list[Candle] = []
        for index, row in enumerate(rows, start=2):
            if not self._row_complete(row):
                self.errors.append(f"Candle incompleto na linha {index}.")
                continue
            timestamp = self._timestamp(row["timestamp"])
            if timestamp is None:
                self.errors.append(f"Timestamp invalido na linha {index}.")
                continue
            self._append_candle(row, timestamp, index, candles)
        return candles

    def _append_candle(
        self,
        row: dict[str, str],
        timestamp: str,
        index: int,
        candles: list[Candle],
    ) -> None:
        try:
            candle = Candle(
                data=timestamp,
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
        candles.append(candle)

    def _normalize_row(self, row: dict[str, str]) -> dict[str, str]:
        lower_row = {
            key.strip().lower(): value.strip()
            for key, value in row.items()
            if key is not None and value is not None
        }
        normalized: dict[str, str] = {}
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

    def _has_required_columns(self, headers: set[str]) -> bool:
        aliases = self._aliases()
        for column in self._required_columns():
            if not any(alias in headers for alias in aliases[column]):
                return False
        return True

    def _row_complete(self, row: dict[str, str]) -> bool:
        return all(row.get(column, "").strip() for column in self._required_columns())

    def _timestamp(self, value: str) -> str | None:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d %H:%M")
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

    def _required_columns(self) -> tuple[str, ...]:
        return ("timestamp", "open", "high", "low", "close", "volume")

    def _aliases(self) -> dict[str, tuple[str, ...]]:
        return {
            "timestamp": ("timestamp", "datetime", "data", "date", "time"),
            "open": ("open", "abertura", "aberto"),
            "high": ("high", "maxima", "max"),
            "low": ("low", "minima", "min"),
            "close": ("close", "fechamento", "ultimo"),
            "volume": ("volume", "vol"),
        }

    def _error(self, message: str) -> HistoricalDataSourceResult:
        self.errors.append(message)
        return HistoricalDataSourceResult(candles=[], errors=list(self.errors))
