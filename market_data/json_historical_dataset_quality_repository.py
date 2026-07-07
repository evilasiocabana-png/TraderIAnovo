"""Adaptador JSON para status de qualidade de datasets historicos."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from market_data.historical_dataset_quality_repository import (
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
)


@dataclass
class JsonHistoricalDatasetQualityRepository(
    HistoricalDatasetQualityRepository
):
    """Persistencia local simples de status historico sem candles."""

    path: Path = Path("data") / "historical_dataset_quality.json"

    def save(self, status: HistoricalDatasetQualityStatus) -> None:
        """Persiste ou atualiza o status por dataset_id."""
        payload = self._read_payload()
        records = {
            item.dataset_id: item
            for item in self._statuses_from_payload(payload)
        }
        records[status.dataset_id] = status
        payload["statuses"] = [asdict(item) for item in records.values()]
        self._write_payload(payload)

    def get(self, dataset_id: str) -> HistoricalDatasetQualityStatus | None:
        """Busca status persistido por dataset_id."""
        for status in self.list_all():
            if status.dataset_id == dataset_id:
                return status
        return None

    def list_all(self) -> list[HistoricalDatasetQualityStatus]:
        """Lista status persistidos em ordem de dataset_id."""
        return sorted(
            self._statuses_from_payload(self._read_payload()),
            key=lambda item: item.dataset_id,
        )

    def append_validation(
        self,
        record: HistoricalDatasetQualityValidationRecord,
    ) -> None:
        """Acrescenta uma validacao ao historico."""
        payload = self._read_payload()
        payload["validations"].append(asdict(record))
        self._write_payload(payload)

    def list_validations(
        self,
        dataset_id: str,
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        """Lista historico de validacoes de um dataset."""
        records = [
            record
            for record in self._validations_from_payload(self._read_payload())
            if record.dataset_id == dataset_id
        ]
        return sorted(records, key=lambda record: record.validated_at)

    def _read_payload(self) -> dict[str, list[dict[str, object]]]:
        if not self.path.exists():
            return {"statuses": [], "validations": []}
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return {"statuses": payload, "validations": []}
        return {
            "statuses": list(payload.get("statuses", [])),
            "validations": list(payload.get("validations", [])),
        }

    def _write_payload(
        self,
        payload: dict[str, list[dict[str, object]]],
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

    def _statuses_from_payload(
        self,
        payload: dict[str, list[dict[str, object]]],
    ) -> list[HistoricalDatasetQualityStatus]:
        return [self._to_status(item) for item in payload["statuses"]]

    def _validations_from_payload(
        self,
        payload: dict[str, list[dict[str, object]]],
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        return [
            self._to_validation_record(item)
            for item in payload["validations"]
        ]

    def _to_status(
        self,
        payload: dict[str, object],
    ) -> HistoricalDatasetQualityStatus:
        return HistoricalDatasetQualityStatus(
            dataset_id=str(payload["dataset_id"]),
            ativo=str(payload["ativo"]),
            timeframe=str(payload["timeframe"]),
            provider=str(payload["provider"]),
            start_date=self._optional_str(payload.get("start_date")),
            end_date=self._optional_str(payload.get("end_date")),
            total_candles=int(payload["total_candles"]),
            quality_status=str(payload["quality_status"]),
            errors=[str(error) for error in payload.get("errors", [])],
            last_validated_at=str(payload["last_validated_at"]),
        )

    def _optional_str(self, value: object | None) -> str | None:
        if value is None:
            return None
        return str(value)

    def _to_validation_record(
        self,
        payload: dict[str, object],
    ) -> HistoricalDatasetQualityValidationRecord:
        return HistoricalDatasetQualityValidationRecord(
            dataset_id=str(payload["dataset_id"]),
            validated_at=str(payload["validated_at"]),
            quality_status=str(payload["quality_status"]),
            total_candles=int(payload["total_candles"]),
            invalid_ohlc_candles=int(payload["invalid_ohlc_candles"]),
            invalid_volume_candles=int(payload["invalid_volume_candles"]),
            temporal_gaps=int(payload["temporal_gaps"]),
            duplicate_timestamps=int(payload["duplicate_timestamps"]),
            messages=[str(message) for message in payload.get("messages", [])],
        )


def create_default_historical_dataset_quality_repository(
) -> HistoricalDatasetQualityRepository:
    """Cria repositorio default de qualidade historica."""
    return JsonHistoricalDatasetQualityRepository()
