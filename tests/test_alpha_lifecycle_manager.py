"""Testes do gerenciador de ciclo de vida de Alphas."""

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha_factory.alpha_lifecycle import (
    AlphaLifecycle,
    AlphaLifecycleStatus,
)
from research.alpha_factory.alpha_lifecycle_manager import AlphaLifecycleManager
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaLifecycleManagerTest(unittest.TestCase):
    """Valida transicoes institucionais do ciclo de vida."""

    def test_manager_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaLifecycleManager))
        self.assertTrue(AlphaLifecycleManager.__dataclass_params__.frozen)

    def test_transicoes_principais_sao_permitidas_em_ordem(self) -> None:
        manager = AlphaLifecycleManager()
        lifecycle = self._lifecycle(AlphaLifecycleStatus.HYPOTHESIS)
        sequence = (
            AlphaLifecycleStatus.PLAYBOOK,
            AlphaLifecycleStatus.IMPLEMENTATION,
            AlphaLifecycleStatus.RESEARCH,
            AlphaLifecycleStatus.VALIDATION,
            AlphaLifecycleStatus.APPROVED,
        )

        for index, target in enumerate(sequence, start=1):
            previous = lifecycle.current_status
            lifecycle = manager.transition(
                lifecycle,
                target,
                datetime(2026, 6, 28, 10, index, 0),
            )

            self.assertEqual(lifecycle.previous_status, previous)
            self.assertEqual(lifecycle.current_status, target)

    def test_deprecated_e_archived_sao_permitidos_apos_aprovacao(self) -> None:
        manager = AlphaLifecycleManager()
        approved = self._lifecycle(AlphaLifecycleStatus.APPROVED)

        deprecated = manager.transition(
            approved,
            AlphaLifecycleStatus.DEPRECATED,
            datetime(2026, 6, 28, 11, 0, 0),
        )
        archived = manager.transition(
            deprecated,
            AlphaLifecycleStatus.ARCHIVED,
            datetime(2026, 6, 28, 12, 0, 0),
        )

        self.assertEqual(deprecated.previous_status, AlphaLifecycleStatus.APPROVED)
        self.assertEqual(deprecated.current_status, AlphaLifecycleStatus.DEPRECATED)
        self.assertEqual(archived.previous_status, AlphaLifecycleStatus.DEPRECATED)
        self.assertEqual(archived.current_status, AlphaLifecycleStatus.ARCHIVED)

    def test_transicao_invalida_e_bloqueada(self) -> None:
        lifecycle = self._lifecycle(AlphaLifecycleStatus.HYPOTHESIS)

        with self.assertRaisesRegex(ValueError, "Transicao invalida"):
            AlphaLifecycleManager().transition(
                lifecycle,
                AlphaLifecycleStatus.RESEARCH,
                datetime(2026, 6, 28, 10, 0, 0),
            )

    def test_nao_permite_retorno_ou_saida_de_archived(self) -> None:
        manager = AlphaLifecycleManager()

        self.assertFalse(
            manager.can_transition(
                AlphaLifecycleStatus.DEPRECATED,
                AlphaLifecycleStatus.APPROVED,
            )
        )
        self.assertFalse(
            manager.can_transition(
                AlphaLifecycleStatus.ARCHIVED,
                AlphaLifecycleStatus.RESEARCH,
            )
        )

    def test_transition_retorna_novo_lifecycle_sem_modificar_original(self) -> None:
        original = self._lifecycle(AlphaLifecycleStatus.HYPOTHESIS)
        updated_at = datetime(2026, 6, 28, 10, 1, 0)

        updated = AlphaLifecycleManager().transition(
            original,
            AlphaLifecycleStatus.PLAYBOOK,
            updated_at,
        )

        self.assertIsNot(updated, original)
        self.assertEqual(original.current_status, AlphaLifecycleStatus.HYPOTHESIS)
        self.assertIsNone(original.previous_status)
        self.assertEqual(updated.current_status, AlphaLifecycleStatus.PLAYBOOK)
        self.assertEqual(updated.previous_status, AlphaLifecycleStatus.HYPOTHESIS)
        self.assertEqual(updated.updated_at, updated_at)

        with self.assertRaises(FrozenInstanceError):
            updated.current_status = AlphaLifecycleStatus.RESEARCH

    def test_manager_nao_executa_pesquisa_ou_acessa_operacao(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_lifecycle_manager.py")
        )
        forbidden_fragments = (
            "ResearchRunner",
            "ResearchPipeline",
            ".run(",
            ".calculate(",
            ".validate(",
            "Dashboard",
            "StrategySignal",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_manager_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_lifecycle_manager.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _lifecycle(
        self,
        status: AlphaLifecycleStatus,
    ) -> AlphaLifecycle:
        return AlphaLifecycle(
            alpha_id="Alpha003",
            current_status=status,
            previous_status=None,
            created_at=datetime(2026, 6, 28, 10, 0, 0),
            updated_at=datetime(2026, 6, 28, 10, 0, 0),
            metadata={"owner": "Research"},
        )


if __name__ == "__main__":
    unittest.main()
