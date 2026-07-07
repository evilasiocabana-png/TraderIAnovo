"""Validador estrutural de metadados historicos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from market_data.contracts import HistoricalDatasetMetadata


REQUIRED_TEXT_FIELDS = (
    "symbol",
    "timeframe",
    "exchange",
    "timezone",
    "source",
    "format",
    "version",
    "first_timestamp",
    "last_timestamp",
)


@dataclass(frozen=True)
class HistoricalDatasetValidationResult:
    """Resultado explicito da validacao de metadados historicos."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


class HistoricalDatasetValidator:
    """Valida metadados historicos sem acessar dados fisicos."""

    def validate(
        self,
        metadata: HistoricalDatasetMetadata | dict[str, Any] | None,
    ) -> HistoricalDatasetValidationResult:
        """Valida contrato ou dict de metadados historicos."""

        errors: list[str] = []
        normalized = self._normalize_metadata(metadata, errors)
        if normalized is None:
            return self._result(errors)

        errors.extend(self._required_field_errors(normalized))
        errors.extend(self._candle_count_errors(normalized))
        errors.extend(self._timestamp_order_errors(normalized))
        return self._result(errors)

    def is_valid(
        self,
        metadata: HistoricalDatasetMetadata | dict[str, Any] | None,
    ) -> bool:
        """Atalho booleano para validacao."""

        return self.validate(metadata).is_valid

    def _normalize_metadata(
        self,
        metadata: HistoricalDatasetMetadata | dict[str, Any] | None,
        errors: list[str],
    ) -> HistoricalDatasetMetadata | None:
        if metadata is None:
            errors.append("HistoricalDatasetMetadata is required.")
            return None
        if isinstance(metadata, HistoricalDatasetMetadata):
            return metadata
        if isinstance(metadata, dict):
            try:
                return HistoricalDatasetMetadata.from_dict(metadata)
            except (TypeError, ValueError) as exc:
                errors.append(f"Invalid HistoricalDatasetMetadata: {exc}")
                return None
        errors.append("metadata must be HistoricalDatasetMetadata or dict.")
        return None

    def _required_field_errors(
        self,
        metadata: HistoricalDatasetMetadata,
    ) -> list[str]:
        errors: list[str] = []
        for field_name in REQUIRED_TEXT_FIELDS:
            value = getattr(metadata, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} is required and must not be empty.")
        return errors

    def _candle_count_errors(
        self,
        metadata: HistoricalDatasetMetadata,
    ) -> list[str]:
        if not isinstance(metadata.candle_count, int):
            return ["candle_count must be an integer."]
        if metadata.candle_count < 0:
            return ["candle_count must be non-negative."]
        return []

    def _timestamp_order_errors(
        self,
        metadata: HistoricalDatasetMetadata,
    ) -> list[str]:
        first = self._parse_timestamp(metadata.first_timestamp)
        last = self._parse_timestamp(metadata.last_timestamp)
        if first is None or last is None:
            return []
        if first > last:
            return ["first_timestamp must be before or equal to last_timestamp."]
        return []

    def _parse_timestamp(self, value: str) -> datetime | None:
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
        return None

    def _result(self, errors: list[str]) -> HistoricalDatasetValidationResult:
        return HistoricalDatasetValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
        )
