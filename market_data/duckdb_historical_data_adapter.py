"""Adaptador DuckDB para a porta de dados historicos."""

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
class DuckDBHistoricalDataAdapter(HistoricalDataAdapter):
    """Le candles historicos a partir de uma origem DuckDB."""

    supported_formats = ("duckdb",)
    adapter_label = "duckdb"
    errors: list[str] = field(default_factory=list)

    def load(self, source: Any) -> HistoricalDataSourceResult:
        """Carrega DuckDB e retorna candles ou erros normalizados."""
        self.errors.clear()
        try:
            rows = self._read_rows(source)
        except ImportError:
            return self._error("Dependencia para leitura DuckDB indisponivel.")
        except (FileNotFoundError, IsADirectoryError, OSError, ValueError) as exc:
            return self._error(f"Origem DuckDB invalida: {exc}")
        if not rows:
            return self._error("DuckDB sem dados.")
        candles = self._candles(rows)
        if self.errors:
            return HistoricalDataSourceResult(candles=[], errors=list(self.errors))
        return HistoricalDataSourceResult(candles=candles, errors=[])

    def _read_rows(self, source: Any) -> list[dict[str, object]]:
        import duckdb

        config = self._source_config(source)
        path = Path(config["database"])
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("banco inexistente.")
        table = str(config["table"]).strip()
        if not table:
            raise ValueError("tabela nao informada.")
        query = self._select_query(table)
        try:
            with duckdb.connect(str(path), read_only=True) as connection:
                columns = [column[0] for column in connection.execute(query).description]
                rows = connection.fetchall()
        except duckdb.Error as exc:
            raise ValueError(str(exc)) from exc
        return [
            self._normalize_row(dict(zip(columns, row, strict=True)))
            for row in rows
        ]

    def _source_config(self, source: Any) -> dict[str, object]:
        if isinstance(source, dict):
            return {
                "database": source.get("database") or source.get("path"),
                "table": source.get("table", "candles"),
            }
        return {"database": source, "table": "candles"}

    def _select_query(self, table: str) -> str:
        return f"SELECT * FROM {self._quoted_identifier(table)} ORDER BY 1"

    def _quoted_identifier(self, value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    def _candles(self, rows: list[dict[str, object]]) -> list[Candle]:
        candles: list[Candle] = []
        if not self._has_required_values(rows[0]):
            self.errors.append("DuckDB com estrutura invalida.")
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
        return all(
            not self._is_missing(row.get(column))
            for column in self._required_columns()
        )

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
