"""Fila em memoria para experimentos do Research Lab."""

from dataclasses import dataclass, field

from research.experiment_management.experiment_definition import ExperimentDefinition


@dataclass
class ExperimentQueue:
    """Gerencia uma fila FIFO de experimentos sem executar pesquisas."""

    _items: list[ExperimentDefinition] = field(default_factory=list, init=False)

    def enqueue(self, experiment: ExperimentDefinition) -> ExperimentDefinition:
        """Adiciona um experimento ao final da fila."""
        self._items.append(experiment)
        return experiment

    def dequeue(self) -> ExperimentDefinition | None:
        """Remove e retorna o proximo experimento da fila."""
        if not self._items:
            return None
        return self._items.pop(0)

    def peek(self) -> ExperimentDefinition | None:
        """Retorna o proximo experimento sem remove-lo."""
        if not self._items:
            return None
        return self._items[0]

    def cancel(self, experiment_id: str) -> bool:
        """Remove um experimento da fila pelo identificador."""
        for index, experiment in enumerate(self._items):
            if experiment.experiment_id == experiment_id:
                del self._items[index]
                return True
        return False

    def clear(self) -> None:
        """Esvazia a fila em memoria."""
        self._items.clear()

    def size(self) -> int:
        """Retorna a quantidade de experimentos na fila."""
        return len(self._items)
