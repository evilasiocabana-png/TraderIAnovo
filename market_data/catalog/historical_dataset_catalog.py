"""Catalogo estrutural de datasets historicos disponiveis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DATASETS_ROOT = Path("historical_data") / "datasets"


@dataclass(frozen=True)
class HistoricalDatasetRecord:
    """Descricao estrutural de um dataset historico."""

    symbol: str
    timeframe: str
    period: str
    path: str
    metadata_path: str | None = None


class HistoricalDatasetCatalog:
    """Descobre datasets historicos sem carregar arquivos de dados."""

    def __init__(self, root: str | Path = DEFAULT_DATASETS_ROOT) -> None:
        self.root = Path(root)

    def list_symbols(self) -> list[str]:
        """Lista ativos disponiveis na estrutura oficial."""

        return self._child_directory_names(self.root)

    def list_timeframes(self, symbol: str) -> list[str]:
        """Lista timeframes disponiveis para um ativo."""

        return self._child_directory_names(self.root / symbol)

    def list_available_periods(self, symbol: str, timeframe: str) -> list[str]:
        """Lista periodos disponiveis para ativo e timeframe."""

        return self._child_directory_names(self.root / symbol / timeframe)

    def dataset_exists(self, symbol: str, timeframe: str, period: str) -> bool:
        """Verifica se a estrutura de um dataset existe."""

        return self._dataset_path(symbol, timeframe, period).is_dir()

    def list_datasets(self) -> list[HistoricalDatasetRecord]:
        """Lista datasets descobertos sem abrir arquivos de dados."""

        records: list[HistoricalDatasetRecord] = []
        for symbol in self.list_symbols():
            for timeframe in self.list_timeframes(symbol):
                for period in self.list_available_periods(symbol, timeframe):
                    records.append(self._record(symbol, timeframe, period))
        return sorted(
            records,
            key=lambda record: (record.symbol, record.timeframe, record.period),
        )

    def get_dataset_metadata(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> dict[str, Any] | None:
        """Retorna metadados declarativos quando o dataset existir."""

        if not self.dataset_exists(symbol, timeframe, period):
            return None

        metadata = self._default_metadata(symbol, timeframe, period)
        metadata_path = self._metadata_path(symbol, timeframe, period)
        if metadata_path.is_file():
            declared = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(declared, dict):
                metadata.update(declared)
                if "format_version" in declared and "version" not in declared:
                    metadata["version"] = declared["format_version"]
        return metadata

    def validate_structure(self) -> dict[str, object]:
        """Valida a estrutura de diretorios sem exigir datasets reais."""

        problems: list[str] = []
        if not self.root.exists():
            problems.append(f"Diretorio raiz ausente: {self.root}")
        elif not self.root.is_dir():
            problems.append(f"Raiz de datasets nao e diretorio: {self.root}")

        for record in self.list_datasets():
            if not record.symbol:
                problems.append(f"Dataset sem symbol: {record.path}")
            if not record.timeframe:
                problems.append(f"Dataset sem timeframe: {record.path}")
            if not record.period:
                problems.append(f"Dataset sem periodo: {record.path}")

        return {
            "valid": not problems,
            "root": str(self.root),
            "dataset_count": len(self.list_datasets()),
            "problems": problems,
        }

    def _record(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> HistoricalDatasetRecord:
        path = self._dataset_path(symbol, timeframe, period)
        metadata_path = self._metadata_path(symbol, timeframe, period)
        return HistoricalDatasetRecord(
            symbol=symbol,
            timeframe=timeframe,
            period=period,
            path=str(path),
            metadata_path=str(metadata_path) if metadata_path.is_file() else None,
        )

    def _default_metadata(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "period": period,
            "source": None,
            "exchange": None,
            "timezone": None,
            "first_timestamp": None,
            "last_timestamp": None,
            "candle_count": None,
            "format": None,
            "version": None,
        }

    def _dataset_path(self, symbol: str, timeframe: str, period: str) -> Path:
        return self.root / symbol / timeframe / period

    def _metadata_path(self, symbol: str, timeframe: str, period: str) -> Path:
        return self._dataset_path(symbol, timeframe, period) / "metadata.json"

    def _child_directory_names(self, path: Path) -> list[str]:
        if not path.is_dir():
            return []
        return sorted(child.name for child in path.iterdir() if child.is_dir())
