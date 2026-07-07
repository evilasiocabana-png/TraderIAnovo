"""Testes da persistencia de qualidade de datasets historicos."""

import tempfile
import unittest
import json
from pathlib import Path

from market_data import (
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
    JsonHistoricalDatasetQualityRepository,
)


class HistoricalDatasetQualityRepositoryTest(unittest.TestCase):
    """Valida adaptador de persistencia sem armazenar candles."""

    def test_salva_e_recupera_status_de_qualidade(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonHistoricalDatasetQualityRepository(
                Path(temp_dir) / "quality.json"
            )
            status = self._status()

            repository.save(status)

            recovered = repository.get("wdo_1m_2026")
            self.assertEqual(recovered, status)

    def test_atualiza_status_existente_por_dataset_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonHistoricalDatasetQualityRepository(
                Path(temp_dir) / "quality.json"
            )
            repository.save(self._status(quality_status="REJECTED"))
            repository.save(self._status(quality_status="APPROVED"))

            statuses = repository.list_all()

            self.assertEqual(len(statuses), 1)
            self.assertEqual(statuses[0].quality_status, "APPROVED")

    def test_persistencia_nao_armazena_candles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "quality.json"
            repository = JsonHistoricalDatasetQualityRepository(path)

            repository.save(self._status())

            payload = json.loads(path.read_text(encoding="utf-8"))
            status = payload["statuses"][0]
            self.assertNotIn("candles", status)
            self.assertNotIn("abertura", status)
            self.assertNotIn("fechamento", status)
            self.assertEqual(status["total_candles"], 2)

    def test_registra_e_consulta_historico_de_validacoes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonHistoricalDatasetQualityRepository(
                Path(temp_dir) / "quality.json"
            )
            first = self._validation_record(validated_at="2026-06-26T18:00:00")
            second = self._validation_record(
                validated_at="2026-06-26T18:05:00",
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
            )

            repository.append_validation(second)
            repository.append_validation(first)

            history = repository.list_validations("wdo_1m_2026")
            self.assertEqual(history, [first, second])

    def test_historico_filtra_por_dataset_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = JsonHistoricalDatasetQualityRepository(
                Path(temp_dir) / "quality.json"
            )
            repository.append_validation(self._validation_record())
            repository.append_validation(
                self._validation_record(dataset_id="outro_dataset")
            )

            history = repository.list_validations("wdo_1m_2026")

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].dataset_id, "wdo_1m_2026")

    def test_historico_nao_armazena_candles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "quality.json"
            repository = JsonHistoricalDatasetQualityRepository(path)

            repository.append_validation(self._validation_record())

            payload = json.loads(path.read_text(encoding="utf-8"))
            record = payload["validations"][0]
            self.assertNotIn("candles", record)
            self.assertNotIn("abertura", record)
            self.assertNotIn("fechamento", record)

    def _status(
        self,
        quality_status: str = "APPROVED",
    ) -> HistoricalDatasetQualityStatus:
        return HistoricalDatasetQualityStatus(
            dataset_id="wdo_1m_2026",
            ativo="WDO",
            timeframe="1m",
            provider="csv",
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:01",
            total_candles=2,
            quality_status=quality_status,
            errors=[],
            last_validated_at="2026-06-26T18:00:00",
        )

    def _validation_record(
        self,
        dataset_id: str = "wdo_1m_2026",
        validated_at: str = "2026-06-26T18:00:00",
        quality_status: str = "APPROVED",
        invalid_ohlc_candles: int = 0,
    ) -> HistoricalDatasetQualityValidationRecord:
        return HistoricalDatasetQualityValidationRecord(
            dataset_id=dataset_id,
            validated_at=validated_at,
            quality_status=quality_status,
            total_candles=2,
            invalid_ohlc_candles=invalid_ohlc_candles,
            invalid_volume_candles=0,
            temporal_gaps=0,
            duplicate_timestamps=0,
            messages=[],
        )


if __name__ == "__main__":
    unittest.main()
