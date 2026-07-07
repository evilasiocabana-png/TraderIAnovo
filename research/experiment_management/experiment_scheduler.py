"""Agendador sequencial de experimentos do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_queue import ExperimentQueue
from research.research_runner import ResearchRunner


ExperimentFactory = Callable[[ExperimentDefinition], object]


@dataclass
class ExperimentScheduler:
    """Consome a fila e delega uma execucao por vez ao ResearchRunner."""

    queue: ExperimentQueue
    runner: ResearchRunner
    experiment_factory: ExperimentFactory
    _processed: list[ExperimentDefinition] = field(default_factory=list, init=False)

    def run_next(self) -> ExperimentDefinition | None:
        """Executa o proximo experimento da fila, quando existir."""
        definition = self.queue.dequeue()
        if definition is None:
            return None

        running_definition = self._with_status(definition, "RUNNING")
        try:
            experiment = self.experiment_factory(running_definition)
            result = self.runner.run(experiment)
            final_status = "COMPLETED" if self._is_success(result) else "FAILED"
        except Exception:
            final_status = "FAILED"

        completed_definition = self._with_status(running_definition, final_status)
        self._processed.append(completed_definition)
        return completed_definition

    def run_all(self) -> tuple[ExperimentDefinition, ...]:
        """Executa a fila de forma sequencial ate esvaziar."""
        executed: list[ExperimentDefinition] = []
        while self.queue.size() > 0:
            result = self.run_next()
            if result is not None:
                executed.append(result)
        return tuple(executed)

    def processed(self) -> tuple[ExperimentDefinition, ...]:
        """Retorna experimentos ja processados pelo scheduler."""
        return tuple(self._processed)

    def _with_status(
        self,
        definition: ExperimentDefinition,
        status: str,
    ) -> ExperimentDefinition:
        return replace(definition, status=status)

    def _is_success(self, result: object) -> bool:
        errors = getattr(result, "errors", ())
        status = getattr(result, "status", "")
        status_value = getattr(status, "value", str(status))
        return status_value == "COMPLETED" and not errors
