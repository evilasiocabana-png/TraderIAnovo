"""Repositorio em memoria para resultados do Research Pipeline."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchResultRepository:
    """Gerencia ResearchExecutionResult em memoria."""

    _results: dict[str, Any] = field(default_factory=dict, init=False)

    def save(self, result: Any) -> Any:
        """Salva ou substitui um resultado de execucao."""
        execution_id = self._execution_id(result)
        self._results[execution_id] = result
        return result

    def get(self, execution_id: str) -> Any | None:
        """Retorna um resultado pelo identificador da execucao."""
        return self._results.get(execution_id)

    def list(self) -> tuple[Any, ...]:
        """Lista resultados armazenados em memoria."""
        return tuple(self._results.values())

    def delete(self, execution_id: str) -> bool:
        """Remove um resultado quando ele existir."""
        if execution_id not in self._results:
            return False
        del self._results[execution_id]
        return True

    def list_by_experiment(self, experiment_id: str) -> tuple[Any, ...]:
        """Lista resultados associados a um experimento."""
        return tuple(
            result
            for result in self._results.values()
            if self._experiment_id(result) == experiment_id
        )

    def _execution_id(self, result: Any) -> str:
        for attribute in ("execution_id", "id"):
            value = getattr(result, attribute, None)
            if value:
                return str(value)
        raise ValueError("Resultado deve possuir execution_id ou id.")

    def _experiment_id(self, result: Any) -> str | None:
        value = getattr(result, "experiment_id", None)
        if value:
            return str(value)
        experiment = getattr(result, "experiment", None)
        if experiment is None:
            return None
        for attribute in ("experiment_id", "id"):
            nested_value = getattr(experiment, attribute, None)
            if nested_value:
                return str(nested_value)
        return None
