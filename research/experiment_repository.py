"""Repositorio em memoria para experimentos do Research Lab."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExperimentRepository:
    """Gerencia experimentos em memoria, sem persistencia externa."""

    _experiments: dict[str, Any] = field(default_factory=dict, init=False)

    def save(self, experiment: Any) -> Any:
        """Salva ou substitui um experimento em memoria."""
        experiment_id = self._experiment_id(experiment)
        self._experiments[experiment_id] = experiment
        return experiment

    def get(self, experiment_id: str) -> Any | None:
        """Retorna um experimento pelo identificador."""
        return self._experiments.get(experiment_id)

    def list(self) -> tuple[Any, ...]:
        """Lista os experimentos armazenados em memoria."""
        return tuple(self._experiments.values())

    def exists(self, experiment_id: str) -> bool:
        """Indica se um experimento existe no repositorio."""
        return experiment_id in self._experiments

    def delete(self, experiment_id: str) -> bool:
        """Remove um experimento quando ele existir."""
        if experiment_id not in self._experiments:
            return False
        del self._experiments[experiment_id]
        return True

    def _experiment_id(self, experiment: Any) -> str:
        for attribute in ("experiment_id", "id"):
            value = getattr(experiment, attribute, None)
            if value:
                return str(value)
        raise ValueError("Experimento deve possuir experiment_id ou id.")
