"""Protecao dos contratos arquiteturais do EventBus."""

import ast
import importlib
from pathlib import Path
import unittest

from core.event_bus import EventBus
from core import events
from tests.architecture_test_utils import imports_from, parse_ast, python_files, read_source


class EventContractsTest(unittest.TestCase):
    """Garante comunicacao por barramento, sem acoplamento direto."""

    PRODUCTION_PATHS = (
        Path("application"),
        Path("core"),
        Path("replay"),
        Path("research"),
        Path("market"),
    )
    PUBLISHER_FILES = (
        Path("core/engine.py"),
        Path("application/replay_service.py"),
        Path("replay/replay_engine.py"),
    )
    SUBSCRIBER_FILES = (
        Path("core/session_manager.py"),
        Path("core/event_logger.py"),
    )

    def test_event_bus_instancia_sem_excecao(self) -> None:
        bus = EventBus()

        self.assertIsInstance(bus, EventBus)

    def test_registro_e_publicacao_de_eventos_funcionam(self) -> None:
        bus = EventBus()
        received: list[dict[str, str]] = []

        bus.subscribe(events.DECISION_CREATED, received.append)
        bus.publish(events.DECISION_CREATED, {"decision": "BUY"})

        self.assertEqual(received, [{"decision": "BUY"}])

    def test_multiplos_subscribers_recebem_evento_publicado(self) -> None:
        bus = EventBus()
        first: list[str] = []
        second: list[str] = []

        bus.subscribe(events.ORDER_CREATED, first.append)
        bus.subscribe(events.ORDER_CREATED, second.append)
        bus.publish(events.ORDER_CREATED, "order-1")

        self.assertEqual(first, ["order-1"])
        self.assertEqual(second, ["order-1"])

    def test_unsubscribe_remove_subscriber_sem_quebrar_publicacao(self) -> None:
        bus = EventBus()
        received: list[str] = []

        bus.subscribe(events.ORDER_CLOSED, received.append)
        bus.unsubscribe(events.ORDER_CLOSED, received.append)
        bus.publish(events.ORDER_CLOSED, "order-1")

        self.assertEqual(received, [])

    def test_eventos_oficiais_continuam_existindo(self) -> None:
        official_events = {
            "SYSTEM_STARTED",
            "NEW_CANDLE",
            "MARKET_DNA_UPDATED",
            "STRATEGY_SIGNAL_CREATED",
            "DECISION_CREATED",
            "ORDER_CREATED",
            "ORDER_CLOSED",
            "BACKTEST_FINISHED",
            "FEATURE_SNAPSHOT_CREATED",
            "REGIME_ANALYSIS_CREATED",
            "RESEARCH_ANALYSIS_CREATED",
        }

        for event_name in official_events:
            with self.subTest(event_name=event_name):
                self.assertTrue(hasattr(events, event_name))
                self.assertIn(getattr(events, event_name), events.OFFICIAL_EVENTS)

    def test_imports_criticos_do_event_bus_nao_quebram(self) -> None:
        event_bus_module = importlib.import_module("core.event_bus")
        events_module = importlib.import_module("core.events")

        self.assertTrue(hasattr(event_bus_module, "EventBus"))
        for optional_contract in ("Event", "EventType", "EventPublisher", "EventSubscriber"):
            if hasattr(event_bus_module, optional_contract):
                self.assertIsNotNone(getattr(event_bus_module, optional_contract))
            if hasattr(events_module, optional_contract):
                self.assertIsNotNone(getattr(events_module, optional_contract))

    def test_publishers_nao_conhecem_subscribers_diretamente(self) -> None:
        forbidden_imports = {
            "core.session_manager",
            "SessionManager",
        }

        for path in self.PUBLISHER_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} conhece subscriber diretamente: "
                    f"{sorted(forbidden_imports & imports)}",
                )

    def test_subscribers_nao_conhecem_publishers_diretamente(self) -> None:
        forbidden_imports = {
            "core.engine",
            "application.replay_service",
            "replay.replay_engine",
            "Engine",
            "ReplayService",
            "ReplayEngine",
        }

        for path in self.SUBSCRIBER_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} conhece publisher diretamente: "
                    f"{sorted(forbidden_imports & imports)}",
                )

    def test_publicacoes_de_producao_usam_constantes_oficiais(self) -> None:
        violations: list[str] = []
        official_names = self._official_event_constant_names()

        for path in self._production_python_files():
            tree = parse_ast(path)
            for node in ast.walk(tree):
                if not self._is_publish_call(node):
                    continue
                event_arg = node.args[0] if node.args else None
                if isinstance(event_arg, ast.Constant) and isinstance(
                    event_arg.value,
                    str,
                ):
                    violations.append(f"{path}:{node.lineno}:{event_arg.value}")
                if isinstance(event_arg, ast.Name) and event_arg.id not in official_names:
                    violations.append(f"{path}:{node.lineno}:{event_arg.id}")

        self.assertEqual(
            violations,
            [],
            "Publicacao de eventos deve usar constantes oficiais: "
            + "; ".join(violations),
        )

    def test_replay_publica_eventos_por_event_bus(self) -> None:
        replay_service_source = read_source(Path("application/replay_service.py"))
        replay_engine_source = read_source(Path("replay/replay_engine.py"))

        self.assertIn("EventBus", replay_service_source)
        self.assertIn("self.event_bus.publish", replay_service_source)
        self.assertIn("EventBus", replay_engine_source)
        self.assertIn("self.event_bus.publish", replay_engine_source)

    def test_research_lab_nao_cria_acoplamento_direto_com_subscribers(self) -> None:
        imports = self._imports(Path("application/research_lab_service.py"))
        forbidden_imports = {
            "core.session_manager",
            "core.event_logger",
            "SessionManager",
            "EventLogger",
        }

        self.assertTrue(
            forbidden_imports.isdisjoint(imports),
            "ResearchLabService nao deve conhecer subscribers diretamente.",
        )

    def test_dashboard_service_nao_bypassa_event_bus_com_acoplamento_direto(
        self,
    ) -> None:
        imports = self._imports(Path("application/dashboard_service.py"))
        forbidden_imports = {
            "core.session_manager",
            "core.engine",
            "replay.replay_engine",
            "research.research_lab",
        }

        self.assertTrue(
            forbidden_imports.isdisjoint(imports),
            f"DashboardService possui acoplamento direto proibido: "
            f"{sorted(forbidden_imports & imports)}",
        )

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _production_python_files(self) -> list[Path]:
        files: list[Path] = []
        for root in self.PRODUCTION_PATHS:
            files.extend(python_files(root))
        return files

    def _official_event_constant_names(self) -> set[str]:
        return {
            name
            for name, value in vars(events).items()
            if name.isupper()
            and isinstance(value, str)
            and value in events.OFFICIAL_EVENTS
        }

    def _is_publish_call(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "publish"
            and bool(node.args)
        )


if __name__ == "__main__":
    unittest.main()
