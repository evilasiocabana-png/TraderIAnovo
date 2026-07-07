"""Testes do registro oficial de Alphas."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from research.portfolio.alpha_registry import AlphaRegistry
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaRegistryTest(unittest.TestCase):
    """Valida registro declarativo de Alphas."""

    def test_registry_inicia_com_alpha001_registrada(self) -> None:
        registry = AlphaRegistry()

        self.assertTrue(registry.exists("Alpha001"))
        self.assertEqual(registry.get("Alpha001")["alpha_id"], "Alpha001")
        self.assertEqual(len(registry.list()), 1)

    def test_register_adiciona_alpha_declarativa_por_alpha_id(self) -> None:
        registry = AlphaRegistry()
        alpha = _Alpha(alpha_id="AlphaXYZ", name="Alpha XYZ")

        saved = registry.register(alpha)

        self.assertIs(saved, alpha)
        self.assertIs(registry.get("AlphaXYZ"), alpha)
        self.assertTrue(registry.exists("AlphaXYZ"))

    def test_register_aceita_dict_com_alpha_id(self) -> None:
        registry = AlphaRegistry()
        alpha = {"alpha_id": "Alpha002", "name": "Alpha 002"}

        registry.register(alpha)

        self.assertIs(registry.get("Alpha002"), alpha)

    def test_register_aceita_id_como_identificador_alternativo(self) -> None:
        registry = AlphaRegistry()
        alpha = _LegacyAlpha(id="AlphaLegacy")

        registry.register(alpha)

        self.assertIs(registry.get("AlphaLegacy"), alpha)

    def test_register_substitui_alpha_com_mesmo_id(self) -> None:
        registry = AlphaRegistry()
        first = _Alpha(alpha_id="AlphaXYZ", name="Primeira")
        second = _Alpha(alpha_id="AlphaXYZ", name="Segunda")

        registry.register(first)
        registry.register(second)

        self.assertIs(registry.get("AlphaXYZ"), second)

    def test_unregister_remove_alpha_existente(self) -> None:
        registry = AlphaRegistry()

        removed = registry.unregister("Alpha001")

        self.assertTrue(removed)
        self.assertFalse(registry.exists("Alpha001"))
        self.assertIsNone(registry.get("Alpha001"))

    def test_unregister_retorna_false_para_alpha_inexistente(self) -> None:
        self.assertFalse(AlphaRegistry().unregister("missing"))

    def test_register_rejeita_alpha_sem_identificador(self) -> None:
        with self.assertRaises(ValueError):
            AlphaRegistry().register(object())

    def test_registry_nao_instancia_estrategias_ou_executa_alpha(self) -> None:
        source = read_source(Path("research/portfolio/alpha_registry.py"))
        forbidden_fragments = (
            "Alpha001IORBStrategy(",
            "Alpha001DecisionEngine(",
            "Alpha001Config(",
            "generate_signal",
            ".run(",
            ".calculate(",
            "Strategy(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_registry_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/alpha_registry.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
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
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


@dataclass(frozen=True)
class _Alpha:
    """Alpha declarativa de teste."""

    alpha_id: str
    name: str


@dataclass(frozen=True)
class _LegacyAlpha:
    """Alpha declarativa com identificador alternativo."""

    id: str


if __name__ == "__main__":
    unittest.main()
