"""Contrato para resultado de validacao estrutural de dataset historico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalDatasetValidationResult:
    """DTO imutavel para representar resultado de validacao historica."""

    dataset_id: str
    is_valid: bool
    records_checked: int
    invalid_records: int
    gap_count: int
    duplicate_timestamp_count: int
    critical_errors: tuple[str, ...]
    warnings: tuple[str, ...]
    validated_at: str
    validator_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.critical_errors, tuple):
            raise TypeError("critical_errors must be a tuple[str, ...]")
        if any(not isinstance(error, str) for error in self.critical_errors):
            raise TypeError("critical_errors must contain only str values")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple[str, ...]")
        if any(not isinstance(warning, str) for warning in self.warnings):
            raise TypeError("warnings must contain only str values")
        for field_name in (
            "records_checked",
            "invalid_records",
            "gap_count",
            "duplicate_timestamp_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
