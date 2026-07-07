"""Gerenciador de transicoes do ciclo de vida de Alphas."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from research.alpha_factory.alpha_lifecycle import (
    AlphaLifecycle,
    AlphaLifecycleStatus,
)


@dataclass(frozen=True)
class AlphaLifecycleManager:
    """Aplica somente transicoes institucionais permitidas."""

    def transition(
        self,
        lifecycle: AlphaLifecycle,
        target_status: AlphaLifecycleStatus,
        updated_at: datetime,
    ) -> AlphaLifecycle:
        """Retorna um novo ciclo de vida quando a transicao for valida."""
        if not self.can_transition(lifecycle.current_status, target_status):
            raise ValueError(
                "Transicao invalida de "
                f"{lifecycle.current_status.value} para {target_status.value}."
            )
        return replace(
            lifecycle,
            previous_status=lifecycle.current_status,
            current_status=target_status,
            updated_at=updated_at,
        )

    def can_transition(
        self,
        current_status: AlphaLifecycleStatus,
        target_status: AlphaLifecycleStatus,
    ) -> bool:
        """Indica se uma transicao direta e permitida."""
        return self._allowed_transitions().get(current_status) == target_status

    def _allowed_transitions(
        self,
    ) -> dict[AlphaLifecycleStatus, AlphaLifecycleStatus]:
        return {
            AlphaLifecycleStatus.HYPOTHESIS: AlphaLifecycleStatus.PLAYBOOK,
            AlphaLifecycleStatus.PLAYBOOK: AlphaLifecycleStatus.IMPLEMENTATION,
            AlphaLifecycleStatus.IMPLEMENTATION: AlphaLifecycleStatus.RESEARCH,
            AlphaLifecycleStatus.RESEARCH: AlphaLifecycleStatus.VALIDATION,
            AlphaLifecycleStatus.VALIDATION: AlphaLifecycleStatus.APPROVED,
            AlphaLifecycleStatus.APPROVED: AlphaLifecycleStatus.DEPRECATED,
            AlphaLifecycleStatus.DEPRECATED: AlphaLifecycleStatus.ARCHIVED,
        }
