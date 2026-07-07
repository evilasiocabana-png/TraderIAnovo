"""Importador oficial de datasets historicos para formato interno."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from market_data.adapters.csv_historical_data_adapter import CsvHistoricalDataAdapter
from market_data.historical_dataset import HistoricalDataset


DEFAULT_INTERNAL_DATASETS_ROOT = Path("historical_data") / "datasets"


@dataclass(frozen=True)
class HistoricalImportResult:
    """Resultado estruturado da importacao historica."""

    dataset: HistoricalDataset
    dataset_path: str
    data_path: str
    metadata_path: str
    imported_candles: int
    duplicated_candles_removed: int
    errors: tuple[str, ...]

    @property
    def success(self) -> bool:
        """Indica se a importacao criou um dataset utilizavel."""

        return not self.errors and not self.dataset.is_empty


@dataclass(frozen=True)
class HistoricalImporter:
    """Importa OHLCV historico para a estrutura interna do TraderIA."""

    root: Path = DEFAULT_INTERNAL_DATASETS_ROOT
    csv_adapter: CsvHistoricalDataAdapter = field(
        default_factory=CsvHistoricalDataAdapter,
    )

    def import_csv(
        self,
        source: str | Path,
        symbol: str,
        timeframe: str,
        period: str | None = None,
        exchange: str = "B3",
        timezone: str = "America/Sao_Paulo",
        version: str = "1.0",
    ) -> HistoricalImportResult:
        """Importa CSV OHLCV e grava dataset normalizado."""

        result = self.csv_adapter.load_candles(source)
        if result.errors:
            return self._failed_result(symbol, timeframe, result.errors)

        candles, duplicates = self._deduplicate_and_sort(result.candles)
        dataset = self._dataset(symbol, timeframe, candles)
        if dataset.is_empty:
            return self._failed_result(symbol, timeframe, ["Dataset historico vazio."])

        resolved_period = period or self._period(dataset)
        dataset_path = self.root / symbol / timeframe / resolved_period
        data_path = dataset_path / "data.csv"
        metadata_path = dataset_path / "metadata.json"

        dataset_path.mkdir(parents=True, exist_ok=True)
        self._write_data(data_path, dataset)
        self._write_metadata(
            metadata_path=metadata_path,
            dataset=dataset,
            source=source,
            exchange=exchange,
            timezone=timezone,
            version=version,
            period=resolved_period,
            duplicates=duplicates,
        )

        return HistoricalImportResult(
            dataset=dataset,
            dataset_path=str(dataset_path),
            data_path=str(data_path),
            metadata_path=str(metadata_path),
            imported_candles=dataset.total_candles,
            duplicated_candles_removed=duplicates,
            errors=(),
        )

    def _deduplicate_and_sort(
        self,
        candles: list[Any],
    ) -> tuple[list[Any], int]:
        by_timestamp: dict[str, Any] = {}
        duplicates = 0
        for candle in candles:
            if candle.data in by_timestamp:
                duplicates += 1
            by_timestamp[candle.data] = candle
        return (
            [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)],
            duplicates,
        )

    def _dataset(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any],
    ) -> HistoricalDataset:
        return HistoricalDataset(
            symbol=symbol,
            timeframe=timeframe,
            start_date=candles[0].data if candles else None,
            end_date=candles[-1].data if candles else None,
            candles=list(candles),
        )

    def _write_data(
        self,
        path: Path,
        dataset: HistoricalDataset,
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=("timestamp", "open", "high", "low", "close", "volume"),
            )
            writer.writeheader()
            for candle in dataset.candles:
                writer.writerow(
                    {
                        "timestamp": candle.data,
                        "open": candle.abertura,
                        "high": candle.maxima,
                        "low": candle.minima,
                        "close": candle.fechamento,
                        "volume": candle.volume,
                    }
                )

    def _write_metadata(
        self,
        metadata_path: Path,
        dataset: HistoricalDataset,
        source: str | Path,
        exchange: str,
        timezone: str,
        version: str,
        period: str,
        duplicates: int,
    ) -> None:
        metadata = {
            "dataset_id": self._dataset_id(dataset.symbol, dataset.timeframe, period),
            "symbol": dataset.symbol,
            "timeframe": dataset.timeframe,
            "source": str(source),
            "exchange": exchange,
            "timezone": timezone,
            "first_timestamp": dataset.start_date,
            "last_timestamp": dataset.end_date,
            "candle_count": dataset.total_candles,
            "format": "csv",
            "version": version,
            "file_path": "data.csv",
            "description": "Dataset historico importado para formato interno.",
            "tags": (
                "historical_importer",
                f"period:{period}",
                f"duplicates_removed:{duplicates}",
            ),
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _failed_result(
        self,
        symbol: str,
        timeframe: str,
        errors: list[str],
    ) -> HistoricalImportResult:
        dataset = HistoricalDataset(
            symbol=symbol,
            timeframe=timeframe,
            start_date=None,
            end_date=None,
            candles=[],
        )
        return HistoricalImportResult(
            dataset=dataset,
            dataset_path="",
            data_path="",
            metadata_path="",
            imported_candles=0,
            duplicated_candles_removed=0,
            errors=tuple(errors),
        )

    def _period(self, dataset: HistoricalDataset) -> str:
        if not dataset.start_date:
            return "UNKNOWN"
        return dataset.start_date[:4]

    def _dataset_id(self, symbol: str, timeframe: str, period: str) -> str:
        return f"{symbol}_{timeframe}_{period}".lower()
