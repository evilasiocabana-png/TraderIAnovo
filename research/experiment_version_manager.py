"""Versionamento em memoria para experimentos do Research Lab."""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class ExperimentVersion:
    """Versao imutavel de um experimento."""

    experiment_id: str
    version: int
    created_at: datetime
    configuration_hash: str


@dataclass(frozen=True)
class ExperimentVersionManager:
    """Gera metadados de versao sem persistir dados."""

    def create_version(
        self,
        experiment_id: str,
        configuration: Any,
        current_version: int | None = None,
    ) -> ExperimentVersion:
        """Cria uma nova versao para a configuracao informada."""
        return ExperimentVersion(
            experiment_id=str(experiment_id),
            version=self.next_version(current_version),
            created_at=datetime.now(),
            configuration_hash=self._configuration_hash(configuration),
        )

    def current_version(
        self,
        version: ExperimentVersion | None,
    ) -> int:
        """Retorna a versao atual conhecida."""
        if version is None:
            return 0
        return version.version

    def next_version(self, current_version: int | None = None) -> int:
        """Calcula o proximo numero de versao."""
        if current_version is None:
            return 1
        return current_version + 1

    def _configuration_hash(self, configuration: Any) -> str:
        payload = self._normalized_payload(configuration)
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _normalized_payload(self, configuration: Any) -> Any:
        if is_dataclass(configuration):
            return asdict(configuration)
        if isinstance(configuration, dict):
            return configuration
        if hasattr(configuration, "__dict__"):
            return vars(configuration)
        return configuration
