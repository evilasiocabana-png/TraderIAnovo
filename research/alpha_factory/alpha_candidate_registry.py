"""Registro em memoria de candidatas a Alpha."""

from dataclasses import dataclass, field, is_dataclass, replace
from typing import Any


@dataclass
class AlphaCandidateRegistry:
    """Gerencia candidatas declarativas sem executar pesquisas."""

    _candidates: dict[str, Any] = field(default_factory=dict, init=False)

    def register(self, candidate: Any) -> Any:
        """Registra ou substitui uma candidata."""
        candidate_id = self._candidate_id(candidate)
        self._candidates[candidate_id] = candidate
        return candidate

    def unregister(self, candidate_id: str) -> bool:
        """Remove uma candidata quando existir."""
        if candidate_id not in self._candidates:
            return False
        del self._candidates[candidate_id]
        return True

    def get(self, candidate_id: str) -> Any | None:
        """Retorna uma candidata pelo identificador."""
        return self._candidates.get(candidate_id)

    def list(self) -> tuple[Any, ...]:
        """Lista candidatas registradas."""
        return tuple(self._candidates.values())

    def approve_for_research(self, candidate_id: str) -> Any | None:
        """Marca uma candidata como aprovada para pesquisa."""
        return self._update_status(candidate_id, "APPROVED_FOR_RESEARCH")

    def reject(self, candidate_id: str) -> Any | None:
        """Marca uma candidata como rejeitada."""
        return self._update_status(candidate_id, "REJECTED")

    def _candidate_id(self, candidate: Any) -> str:
        if isinstance(candidate, dict):
            value = candidate.get("candidate_id") or candidate.get("id")
            if value:
                return str(value)
        for attribute in ("candidate_id", "id"):
            value = getattr(candidate, attribute, None)
            if value:
                return str(value)
        raise ValueError("Candidata deve possuir candidate_id ou id.")

    def _update_status(self, candidate_id: str, status: str) -> Any | None:
        candidate = self.get(candidate_id)
        if candidate is None:
            return None
        updated = self._with_status(candidate, status)
        self._candidates[candidate_id] = updated
        return updated

    def _with_status(self, candidate: Any, status: str) -> Any:
        if isinstance(candidate, dict):
            updated = dict(candidate)
            updated["status"] = status
            return updated
        if is_dataclass(candidate) and hasattr(candidate, "status"):
            return replace(candidate, status=status)
        if hasattr(candidate, "status"):
            setattr(candidate, "status", status)
        return candidate
