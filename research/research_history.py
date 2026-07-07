"""Historico oficial de pesquisas executadas."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.research_result_repository import ResearchResultRepository


@dataclass
class ResearchHistory:
    """Consulta resultados de pesquisa a partir dos repositorios existentes."""

    result_repository: ResearchResultRepository = field(
        default_factory=ResearchResultRepository,
    )

    def list_all(self) -> tuple[Any, ...]:
        """Lista todas as pesquisas registradas."""
        return self.result_repository.list()

    def list_by_alpha(self, alpha: str) -> tuple[Any, ...]:
        """Lista pesquisas associadas a uma Alpha."""
        return tuple(
            result
            for result in self.list_all()
            if self._alpha(result) == alpha
        )

    def list_by_version(self, version: int | str) -> tuple[Any, ...]:
        """Lista pesquisas associadas a uma versao."""
        return tuple(
            result
            for result in self.list_all()
            if self._version(result) == str(version)
        )

    def list_by_period(
        self,
        start: datetime,
        end: datetime,
    ) -> tuple[Any, ...]:
        """Lista pesquisas iniciadas dentro de um periodo."""
        return tuple(
            result
            for result in self.list_all()
            if self._within_period(result, start, end)
        )

    def latest(self) -> Any | None:
        """Retorna a pesquisa mais recente, quando existir."""
        results = self.list_all()
        if not results:
            return None
        return max(results, key=self._timestamp)

    def _alpha(self, result: Any) -> str | None:
        for attribute in ("alpha", "alpha_name", "alpha_id"):
            value = getattr(result, attribute, None)
            if value:
                return str(value)
        experiment = getattr(result, "experiment", None)
        if experiment is None:
            return None
        for attribute in ("alpha", "alpha_name", "alpha_id"):
            value = getattr(experiment, attribute, None)
            if value:
                return str(value)
        return None

    def _version(self, result: Any) -> str | None:
        for attribute in ("version", "experiment_version"):
            value = getattr(result, attribute, None)
            if value is not None:
                return str(value)
        experiment = getattr(result, "experiment", None)
        if experiment is None:
            return None
        for attribute in ("version", "experiment_version"):
            value = getattr(experiment, attribute, None)
            if value is not None:
                return str(value)
        return None

    def _within_period(
        self,
        result: Any,
        start: datetime,
        end: datetime,
    ) -> bool:
        timestamp = self._timestamp(result)
        return start <= timestamp <= end

    def _timestamp(self, result: Any) -> datetime:
        for attribute in ("started_at", "created_at", "finished_at"):
            value = getattr(result, attribute, None)
            if isinstance(value, datetime):
                return value
        return datetime.min
