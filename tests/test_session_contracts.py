"""Contratos arquiteturais da sessao operacional."""

from __future__ import annotations

import ast
import importlib
from dataclasses import fields, is_dataclass
from pathlib import Path
import unittest

from application.dashboard_service import DashboardData, DashboardService
from application.session_service import (
    SessionService,
    SessionSnapshot,
    empty_session_snapshot,
)
from core.event_bus import EventBus
from core.events import (
    DECISION_CREATED,
    ORDER_CLOSED,
    ORDER_CREATED,
    STRATEGY_SIGNAL_CREATED,
    SYSTEM_STARTED,
)
from core.operation_session import OperationSession
from core.session_manager import SessionManager
from tests.architecture_test_utils import calls_from, imports_from, parse_ast, read_source


class SessionContractsTest(unittest.TestCase):
    """Protege OperationSession, SessionManager e SessionService."""

    SESSION_FIELDS = {
        "session_date",
        "market_open_time",
        "market_close_time",
        "operations_today",
        "wins_today",
        "losses_today",
        "gross_profit",
        "gross_loss",
        "net_profit",
        "current_position",
        "last_signal",
        "last_event",
        "system_status",
    }
    SESSION_SNAPSHOT_FIELDS = {
        "session_date",
        "system_status",
        "operations_today",
        "wins_today",
        "losses_today",
        "gross_profit",
        "gross_loss",
        "net_profit",
        "current_position",
        "last_signal",
        "last_event",
    }
    OPERATION_SESSION_METHODS = {
        "register_operation",
        "register_win",
        "register_loss",
        "update_position",
        "update_last_signal",
        "update_last_event",
        "reset_session",
    }
    SESSION_COMPONENT_FILES = (
        Path("core/operation_session.py"),
        Path("core/session_manager.py"),
        Path("application/session_service.py"),
        Path("application/dashboard_service.py"),
    )

    def test_componentes_de_sessao_importam_sem_excecao(self) -> None:
        components = {
            "core.operation_session": ("OperationSession",),
            "core.session_manager": ("SessionManager",),
            "application.session_service": (
                "SessionService",
                "SessionSnapshot",
                "empty_session_snapshot",
            ),
            "application.dashboard_service": ("DashboardService",),
        }

        for module_name, names in components.items():
            module = importlib.import_module(module_name)
            for name in names:
                with self.subTest(component=f"{module_name}.{name}"):
                    self.assertTrue(hasattr(module, name))

    def test_componentes_de_sessao_instanciam_sem_excecao(self) -> None:
        session = self._session()
        bus = EventBus()

        self.assertIsInstance(session, OperationSession)
        self.assertIsInstance(SessionManager(bus, session), SessionManager)
        self.assertIsInstance(SessionService(session), SessionService)
        self.assertIsInstance(DashboardService(), DashboardService)

    def test_operation_session_mantem_campos_essenciais(self) -> None:
        self.assertTrue(is_dataclass(OperationSession))
        field_names = {field.name for field in fields(OperationSession)}

        self.assertEqual(self.SESSION_FIELDS - field_names, set())

    def test_session_snapshot_mantem_campos_expostos_ao_dashboard(self) -> None:
        self.assertTrue(is_dataclass(SessionSnapshot))
        field_names = {field.name for field in fields(SessionSnapshot)}

        self.assertEqual(self.SESSION_SNAPSHOT_FIELDS - field_names, set())

    def test_estado_inicial_da_sessao_operacional_e_consistente(self) -> None:
        session = self._session()

        self.assertEqual(session.session_date, "2026-06-26")
        self.assertEqual(session.market_open_time, "09:00")
        self.assertEqual(session.market_close_time, "18:00")
        self.assertEqual(session.operations_today, 0)
        self.assertEqual(session.wins_today, 0)
        self.assertEqual(session.losses_today, 0)
        self.assertEqual(session.gross_profit, 0.0)
        self.assertEqual(session.gross_loss, 0.0)
        self.assertEqual(session.net_profit, 0.0)
        self.assertIsNone(session.current_position)
        self.assertIsNone(session.last_signal)
        self.assertIsNone(session.last_event)
        self.assertIn("Simula", session.system_status)

    def test_operation_session_expoe_metodos_publicos_de_mutacao_em_memoria(
        self,
    ) -> None:
        methods = self._public_methods(
            Path("core/operation_session.py"),
            "OperationSession",
        )

        self.assertEqual(self.OPERATION_SESSION_METHODS - methods, set())

    def test_operation_session_atualiza_metricas_e_reseta_estado(self) -> None:
        session = self._session()

        session.register_operation()
        session.register_win(120.0)
        session.register_loss(-40.0)
        session.update_position("comprado")
        session.update_last_signal("BUY")
        session.update_last_event(ORDER_CREATED)

        self.assertEqual(session.operations_today, 1)
        self.assertEqual(session.wins_today, 1)
        self.assertEqual(session.losses_today, 1)
        self.assertEqual(session.gross_profit, 120.0)
        self.assertEqual(session.gross_loss, 40.0)
        self.assertEqual(session.net_profit, 80.0)
        self.assertEqual(session.current_position, "comprado")
        self.assertEqual(session.last_signal, "BUY")
        self.assertEqual(session.last_event, ORDER_CREATED)

        session.reset_session()

        self.assertEqual(session.operations_today, 0)
        self.assertEqual(session.net_profit, 0.0)
        self.assertIsNone(session.current_position)
        self.assertIsNone(session.last_signal)
        self.assertIsNone(session.last_event)

    def test_session_service_expoe_snapshot_publico_seguro(self) -> None:
        service = SessionService(self._session())
        methods = self._public_methods(
            Path("application/session_service.py"),
            "SessionService",
        )

        snapshot = service.get_session_snapshot()

        self.assertEqual(methods, {"get_session_snapshot"})
        self.assertIsInstance(snapshot, SessionSnapshot)
        self.assertEqual(snapshot.session_date, "2026-06-26")
        self.assertEqual(snapshot.operations_today, 0)

    def test_empty_session_snapshot_mantem_estado_vazio_controlado(self) -> None:
        snapshot = empty_session_snapshot()

        self.assertIsInstance(snapshot, SessionSnapshot)
        self.assertEqual(snapshot.session_date, "N/D")
        self.assertEqual(snapshot.system_status, "Sessao nao disponivel")
        self.assertEqual(snapshot.operations_today, 0)
        self.assertIsNone(snapshot.current_position)

    def test_session_manager_atualiza_sessao_por_event_bus(self) -> None:
        bus = EventBus()
        session = self._session()
        SessionManager(bus, session).subscribe()

        bus.publish(SYSTEM_STARTED, {})
        bus.publish(STRATEGY_SIGNAL_CREATED, "BUY")
        bus.publish(ORDER_CREATED, {"order": "paper"})
        bus.publish(DECISION_CREATED, {"decision": "BUY"})
        bus.publish(ORDER_CLOSED, {"order": "paper"})

        self.assertEqual(session.operations_today, 1)
        self.assertEqual(session.last_signal, "BUY")
        self.assertEqual(session.last_event, ORDER_CLOSED)

    def test_dashboard_service_expoe_sessao_via_fachada(self) -> None:
        service = DashboardService(session_service=SessionService(self._session()))

        data = service.get_dashboard_data()

        self.assertIsInstance(data, DashboardData)
        self.assertIsInstance(data.session_snapshot, SessionSnapshot)
        self.assertEqual(data.session_snapshot.session_date, "2026-06-26")

    def test_dashboard_app_nao_importa_sessao_diretamente(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))
        forbidden = {
            "core.operation_session",
            "core.session_manager",
            "core.event_bus",
            "application.session_service",
            "OperationSession",
            "SessionManager",
            "SessionService",
            "EventBus",
            "database",
            "sqlite3",
            "market_data",
            "providers",
            "adapters",
        }

        self.assertTrue(
            forbidden.isdisjoint(imports),
            f"dashboard_app.py acessa sessao diretamente: "
            f"{sorted(forbidden & imports)}",
        )
        self.assertIn("application.dashboard_service", imports)

    def test_dashboard_app_renderiza_sessao_operacional_via_snapshot(self) -> None:
        source = read_source(Path("dashboard_app.py"))

        self.assertIn("Sessão Operacional", source)
        for field_name in self.SESSION_SNAPSHOT_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(f"session.{field_name}", source)

    def test_componentes_de_sessao_nao_importam_ui_broker_ou_data_source(self) -> None:
        forbidden = {
            "dashboard_app",
            "streamlit",
            "broker",
            "core.broker",
            "corretora",
            "mt5",
            "MetaTrader5",
            "pandas",
            "duckdb",
            "market_data",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }

        for path in self.SESSION_COMPONENT_FILES:
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                forbidden_for_path = set(forbidden)
                if path == Path("application/dashboard_service.py"):
                    forbidden_for_path.discard("market_data")
                self.assertTrue(
                    forbidden_for_path.isdisjoint(imports),
                    f"{path} importou acoplamento proibido: "
                    f"{sorted(forbidden_for_path & imports)}",
                )

    def test_componentes_de_sessao_nao_acessam_arquivos_fisicos(self) -> None:
        forbidden_calls = {
            "open",
            "read_csv",
            "read_parquet",
            "connect",
            "glob",
            "iterdir",
            "listdir",
        }

        for path in self.SESSION_COMPONENT_FILES:
            with self.subTest(path=str(path)):
                calls = self._calls(path)
                self.assertTrue(
                    forbidden_calls.isdisjoint(calls),
                    f"{path} acessa arquivo/persistencia diretamente: "
                    f"{sorted(forbidden_calls & calls)}",
                )

    def _session(self) -> OperationSession:
        return OperationSession("2026-06-26", "09:00", "18:00")

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _calls(self, path: Path) -> set[str]:
        return calls_from(path)

    def _public_methods(self, path: Path, class_name: str) -> set[str]:
        for node in ast.walk(parse_ast(path)):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return {
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                    and not item.name.startswith("_")
                }
        return set()


if __name__ == "__main__":
    unittest.main()
