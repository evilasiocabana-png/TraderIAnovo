"""Testes do Data Readiness Gate para datasets DuckDB."""

import ast
from pathlib import Path
import tempfile
import unittest

import duckdb
import pandas as pd

from application.data_readiness_gate_log import InMemoryDataReadinessGateLogger
from application.dashboard_service import DashboardService
from application.research_lab_service import ResearchLabService
from market_data import (
    DuckDBHistoricalDataAdapter,
    HistoricalDataProvider,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
)


class DuckDBReadinessGateTest(unittest.TestCase):
    """Valida que DuckDB usa o mesmo readiness gate dos demais providers."""

    def test_duckdb_sem_validacao_retorna_not_validated_e_bloqueia_fluxos(
        self,
    ) -> None:
        logger = InMemoryDataReadinessGateLogger()
        service = self._service_for_duckdb_gate(
            InMemoryHistoricalDatasetQualityRepository(),
            logger,
        )

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "NOT_VALIDATED")
        with self.assertRaisesRegex(ValueError, "NOT_VALIDATED"):
            service.load_selected_historical_dataset_to_replay()
        with self.assertRaisesRegex(ValueError, "NOT_VALIDATED"):
            service.run_selected_historical_dataset_research_experiment()
        self.assertEqual(
            [log.decision for log in service.list_data_readiness_gate_logs()],
            ["BLOCKED", "BLOCKED"],
        )
        self.assertEqual(
            [log.provider for log in service.list_data_readiness_gate_logs()],
            ["duckdb", "duckdb"],
        )
        self.assertTrue(
            all(
                log.__class__.__name__ == "DataReadinessGateLog"
                for log in service.list_data_readiness_gate_logs()
            )
        )

    def test_duckdb_invalido_retorna_not_ready_e_bloqueia_fluxos(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                messages=["1 candle(s) com OHLC invalido."],
            )
        )
        service = self._service_for_duckdb_gate(repository, logger)

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "NOT_READY")
        self.assertIn("OHLC invalido", "; ".join(readiness.reasons))
        with self.assertRaisesRegex(ValueError, "NOT_READY"):
            service.load_selected_historical_dataset_to_replay()
        with self.assertRaisesRegex(ValueError, "NOT_READY"):
            service.run_selected_historical_dataset_research_experiment()
        self.assertEqual(
            [log.decision for log in service.list_data_readiness_gate_logs()],
            ["BLOCKED", "BLOCKED"],
        )
        self.assertEqual(
            [log.provider for log in service.list_data_readiness_gate_logs()],
            ["duckdb", "duckdb"],
        )

    def test_duckdb_aprovado_libera_replay_e_research(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(self._validation_record(total_candles=3))
        service = self._service_for_duckdb_gate(repository, logger)

        readiness = service.get_selected_historical_dataset_readiness()
        replay_data = service.load_selected_historical_dataset_to_replay()
        experiment = service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(readiness.readiness, "READY_FOR_REPLAY_AND_RESEARCH")
        self.assertEqual(replay_data.total_candles, 3)
        self.assertEqual(experiment.experiment_name, "wdo_duckdb_gate")
        self.assertEqual(
            [log.decision for log in service.list_data_readiness_gate_logs()],
            ["ALLOWED", "ALLOWED"],
        )
        self.assertEqual(
            [log.requested_action for log in service.list_data_readiness_gate_logs()],
            ["REPLAY", "RESEARCH"],
        )
        self.assertEqual(
            [log.provider for log in service.list_data_readiness_gate_logs()],
            ["duckdb", "duckdb"],
        )

    def test_camadas_superiores_nao_acessam_duckdb_diretamente(self) -> None:
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

    def _service_for_duckdb_gate(
        self,
        repository: HistoricalDatasetQualityRepository,
        logger: InMemoryDataReadinessGateLogger,
    ) -> DashboardService:
        data_source = DuckDBHistoricalDataAdapter()
        provider = HistoricalDataProvider(data_source=data_source)
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(
            HistoricalDatasetMetadata(
                dataset_id="wdo_duckdb_gate",
                ativo="WDO",
                timeframe="1m",
                start_date="2026-06-26 09:00",
                end_date="2026-06-26 09:02",
                estimated_candles=3,
                provider="duckdb",
            ),
            source=self._valid_duckdb(),
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
            data_readiness_gate_logger=logger,
            research_lab_service=ResearchLabService(market_data_provider=provider),
        )
        service.select_historical_dataset("wdo_duckdb_gate")
        return service

    def _validation_record(
        self,
        quality_status: str = "APPROVED",
        total_candles: int = 3,
        invalid_ohlc_candles: int = 0,
        invalid_volume_candles: int = 0,
        temporal_gaps: int = 0,
        duplicate_timestamps: int = 0,
        messages: list[str] | None = None,
    ) -> HistoricalDatasetQualityValidationRecord:
        return HistoricalDatasetQualityValidationRecord(
            dataset_id="wdo_duckdb_gate",
            validated_at="2026-06-26T18:00:00",
            quality_status=quality_status,
            total_candles=total_candles,
            invalid_ohlc_candles=invalid_ohlc_candles,
            invalid_volume_candles=invalid_volume_candles,
            temporal_gaps=temporal_gaps,
            duplicate_timestamps=duplicate_timestamps,
            messages=list(messages or []),
        )

    def _valid_duckdb(self) -> Path:
        rows = []
        for index in range(3):
            close = 100.0 + index
            rows.append(
                {
                    "datetime": f"2026-06-26 09:{index:02d}",
                    "open": close - 1,
                    "high": close + 2,
                    "low": close - 2,
                    "close": close,
                    "volume": 1000,
                }
            )
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
    """Repositorio em memoria para status e historico de qualidade."""

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
