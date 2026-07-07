"""Registro oficial de Alphas disponiveis para pesquisa."""

from dataclasses import dataclass, field
from typing import Any


DEFAULT_ALPHA001: dict[str, str] = {
    "alpha_id": "Alpha001",
    "name": "Alpha001",
    "description": "Alpha 001 IORB registrada para pesquisa.",
}


@dataclass
class AlphaRegistry:
    """Gerencia Alphas registradas sem instanciar estrategias."""

    _alphas: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.register(DEFAULT_ALPHA001)

    def register(self, alpha: Any) -> Any:
        """Registra ou substitui uma Alpha declarativa."""
        alpha_id = self._alpha_id(alpha)
        self._alphas[alpha_id] = alpha
        return alpha

    def unregister(self, alpha_id: str) -> bool:
        """Remove uma Alpha registrada quando existir."""
        if alpha_id not in self._alphas:
            return False
        del self._alphas[alpha_id]
        return True

    def get(self, alpha_id: str) -> Any | None:
        """Retorna uma Alpha registrada pelo identificador."""
        return self._alphas.get(alpha_id)

    def list(self) -> tuple[Any, ...]:
        """Lista as Alphas registradas."""
        return tuple(self._alphas.values())

    def exists(self, alpha_id: str) -> bool:
        """Indica se uma Alpha esta registrada."""
        return alpha_id in self._alphas

    def _alpha_id(self, alpha: Any) -> str:
        if isinstance(alpha, dict):
            value = alpha.get("alpha_id") or alpha.get("id")
            if value:
                return str(value)
        for attribute in ("alpha_id", "id"):
            value = getattr(alpha, attribute, None)
            if value:
                return str(value)
        raise ValueError("Alpha deve possuir alpha_id ou id.")
