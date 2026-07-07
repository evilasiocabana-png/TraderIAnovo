"""Testes do contrato oficial de ciclo de vida de Alpha."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import unittest
from typing import Mapping, get_type_hints

from research.alpha_factory.alpha_lifecycle import (
    AlphaLifecycle,
    AlphaLifecycleStatus,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaLifecycleTest(unittest.TestCase):
    """Valida contrato imutavel do ciclo de vida de uma Alpha."""

    def test_lifecycle_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaLifecycle))
        self.assertTrue(AlphaLifecycle.__dataclass_params__.frozen)

    def test_status_e_enum_com_estados_obrigatorios(self) -> None:
        self.assertTrue(issubclass(AlphaLifecycleStatus, Enum))
        self.assertEqual(
            [status.name for status in AlphaLifecycleStatus],
            [
                "HYPOTHESIS",
                "PLAYBOOK",
                "IMPLEMENTATION",
                "RESEARCH",
                "VALIDATION",
                "APPROVED",
                "DEPRECATED",
                "ARCHIVED",
            ],
        )

    def test_lifecycle_contem_campos_obrigatorios(self) -> None:
        created_at = datetime(2026, 6, 28, 10, 0, 0)
        updated_at = datetime(2026, 6, 28, 10, 30, 0)
        lifecycle = AlphaLifecycle(
            alpha_id="Alpha003",
            current_status=AlphaLifecycleStatus.RESEARCH,
            previous_status=AlphaLifecycleStatus.IMPLEMENTATION,
            created_at=created_at,
            updated_at=updated_at,
            metadata={"owner": "Research"},
        )

        self.assertEqual(lifecycle.alpha_id, "Alpha003")
        self.assertEqual(lifecycle.current_status, AlphaLifecycleStatus.RESEARCH)
        self.assertEqual(
            lifecycle.previous_status,
            AlphaLifecycleStatus.IMPLEMENTATION,
        )
        self.assertEqual(lifecycle.created_at, created_at)
        self.assertEqual(lifecycle.updated_at, updated_at)
        self.assertEqual(lifecycle.metadata["owner"], "Research")

    def test_lifecycle_aceita_status_anterior_ausente(self) -> None:
        lifecycle = AlphaLifecycle(
            alpha_id="AlphaCandidate",
            current_status=AlphaLifecycleStatus.HYPOTHESIS,
            previous_status=None,
            created_at=datetime(2026, 6, 28, 10, 0, 0),
            updated_at=datetime(2026, 6, 28, 10, 0, 0),
            metadata={},
        )

        self.assertIsNone(lifecycle.previous_status)

    def test_lifecycle_possui_type_hints_completos(self) -> None:
        hints = get_type_hints(AlphaLifecycle)

        self.assertEqual(hints["alpha_id"], str)
        self.assertEqual(hints["current_status"], AlphaLifecycleStatus)
        self.assertEqual(
            hints["previous_status"],
            AlphaLifecycleStatus | None,
        )
        self.assertEqual(hints["created_at"], datetime)
        self.assertEqual(hints["updated_at"], datetime)
        self.assertEqual(hints["metadata"], Mapping[str, object])
        self.assertEqual(
            [field.name for field in fields(AlphaLifecycle)],
            [
                "alpha_id",
                "current_status",
                "previous_status",
                "created_at",
                "updated_at",
                "metadata",
            ],
        )

    def test_lifecycle_e_imutavel(self) -> None:
        lifecycle = AlphaLifecycle(
            alpha_id="Alpha003",
            current_status=AlphaLifecycleStatus.RESEARCH,
            previous_status=AlphaLifecycleStatus.IMPLEMENTATION,
            created_at=datetime(2026, 6, 28, 10, 0, 0),
            updated_at=datetime(2026, 6, 28, 10, 30, 0),
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            lifecycle.current_status = AlphaLifecycleStatus.APPROVED

    def test_nao_implementa_transicoes_ou_execucao(self) -> None:
        source = read_source(Path("research/alpha_factory/alpha_lifecycle.py"))
        forbidden_fragments = (
            "transition",
            "advance",
            "approve(",
            "archive(",
            "deprecated(",
            ".run(",
            ".calculate(",
            ".validate(",
            "ResearchPipeline(",
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

    def test_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_lifecycle.py")
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


if __name__ == "__main__":
    unittest.main()
