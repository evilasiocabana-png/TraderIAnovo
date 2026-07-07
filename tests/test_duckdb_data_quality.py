"""Testes de Data Quality para datasets historicos DuckDB."""

import ast
from pathlib import Path
import tempfile
import unittest

import duckdb
import pandas as pd

from application.dashboard_service import DashboardService
from market_data import (
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
)


class DuckDBDataQualityTest(unittest.TestCase):
    """Valida que DuckDB usa o mesmo fluxo de qualidade do CSV e Parquet."""

    def test_dashboard_service_analisa_qualidade_de_dataset_duckdb(
        self,
    ) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        service = self._service_for_duckdb_quality(repository)

        service.select_historical_dataset("wdo_duckdb_quality")
        report = service.analyze_selected_historical_dataset_quality()

        self.assertEqual(report.dataset_id, "wdo_duckdb_quality")
        self.assertEqual(report.total_candles, 3)
        self.assertEqual(report.start_datetime, "2026-06-26 09:00")
        self.assertEqual(report.end_datetime, "2026-06-26 09:02")
        self.assertEqual(report.invalid_ohlc_candles, 0)
        self.assertEqual(report.invalid_volume_candles, 0)
        self.assertEqual(report.temporal_gaps, 1)
        self.assertEqual(report.duplicate_timestamps, 1)

    def test_status_e_historico_de_qualidade_preservam_provider_duckdb(
        self,
    ) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        service = self._service_for_duckdb_quality(repository)

        service.select_historical_dataset("wdo_duckdb_quality")
        service.analyze_selected_historical_dataset_quality()

        status = repository.get("wdo_duckdb_quality")
        history = repository.list_validations("wdo_duckdb_quality")
        self.assertIsNotNone(status)
        self.assertEqual(status.provider, "duckdb")
        self.assertEqual(status.total_candles, 3)
        self.assertEqual(status.quality_status, "REJECTED")
        self.assertIn("1 gap(s) temporal(is) detectado(s)", status.errors)
        self.assertIn("1 timestamp(s) duplicado(s)", status.errors)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].quality_status, "REJECTED")
        self.assertEqual(history[0].total_candles, 3)
        self.assertEqual(history[0].invalid_ohlc_candles, 0)
        self.assertEqual(history[0].invalid_volume_candles, 0)
        self.assertEqual(history[0].temporal_gaps, 1)
        self.assertEqual(history[0].duplicate_timestamps, 1)

    def test_dashboard_replay_research_nao_acessam_duckdb_diretamente(
        self,
    ) -> None:
        forbidden_terms = (
            "DuckDBHistoricalDataAdapter",
            "duckdb_historical_data_adapter",
            "import duckdb",
            "duckdb.connect",
        )
        for path in self._upper_layer_files():
            source = path.read_text(encoding="utf-8")
            imports = self._imports(path)
            with self.subTest(path=str(path)):
                for term in forbidden_terms:
                    self.assertNotIn(term, source)
                self.assertNotIn("market_data.duckdb_historical_data_adapter", imports)

    def _service_for_duckdb_quality(
        self,
        repository: HistoricalDatasetQualityRepository,
    ) -> DashboardService:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(
            HistoricalDatasetMetadata(
                dataset_id="wdo_duckdb_quality",
                ativo="WDO",
                timeframe="1m",
                start_date="2026-06-26 09:00",
                end_date="2026-06-26 09:02",
                estimated_candles=3,
                provider="duckdb",
            ),
            source=self._duckdb_with_gap_and_duplicate(),
        )
        return DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=HistoricalDataProvider(
                data_source=DuckDBHistoricalDataAdapter(),
            ),
            historical_dataset_quality_repository=repository,
        )

    def _duckdb_with_gap_and_duplicate(self) -> Path:
        rows = [
            {
                "datetime": "2026-06-26 09:00",
                "open": 100.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "volume": 1000,
            },
            {
                "datetime": "2026-06-26 09:02",
                "open": 101.0,
                "high": 103.0,
                "low": 99.0,
                "close": 102.0,
                "volume": 1100,
            },
            {
                "datetime": "2026-06-26 09:02",
                "open": 102.0,
                "high": 104.0,
                "low": 100.0,
                "close": 103.0,
                "volume": 1200,
            },
        ]
        return self._duckdb_from_rows(rows)

    def _duckdb_from_rows(self, rows: list[dict[str, object]]) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb")
        handle.close()
        path = Path(handle.name)
        path.unlink(missing_ok=True)
        frame = pd.DataFrame(rows)
        with duckdb.connect(str(path)) as connection:
            connection.execute("CREATE TABLE candles AS SELECT * FROM frame")
        return path

    def _upper_layer_files(self) -> list[Path]:
        return [
            Path("application") / "replay_service.py",
            Path("application") / "research_lab_service.py",
            Path("dashboard_app.py"),
        ]

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


class InMemoryHistoricalDatasetQualityRepository(
    HistoricalDatasetQualityRepository
):
    """Repositorio em memoria para validar persistencia da qualidade."""

    def __init__(self) -> None:
        self.statuses: dict[str, HistoricalDatasetQualityStatus] = {}
        self.validations: list[HistoricalDatasetQualityValidationRecord] = []

    def save(self, status: HistoricalDatasetQualityStatus) -> None:
        self.statuses[status.dataset_id] = status

    def get(self, dataset_id: str) -> HistoricalDatasetQualityStatus | None:
        return self.statuses.get(dataset_id)

    def list_all(self) -> list[HistoricalDatasetQualityStatus]:
        return list(self.statuses.values())

    def append_validation(
        self,
        record: HistoricalDatasetQualityValidationRecord,
    ) -> None:
        self.validations.append(record)

    def list_validations(
        self,
        dataset_id: str,
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        return [
            record
            for record in self.validations
            if record.dataset_id == dataset_id
        ]


if __name__ == "__main__":
    unittest.main()
