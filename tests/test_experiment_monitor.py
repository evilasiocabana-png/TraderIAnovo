"""Testes do monitor de execucao de experimentos."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
import unittest

from research.experiment_management.experiment_monitor import (
    ExperimentExecutionStatus,
    ExperimentMonitor,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentMonitorTest(unittest.TestCase):
    """Valida monitoramento sem execucao de experimentos."""

    def test_status_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentExecutionStatus))
        self.assertTrue(ExperimentExecutionStatus.__dataclass_params__.frozen)

    def test_status_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ExperimentExecutionStatus)]

        self.assertEqual(
            field_names,
            [
                "experiment_id",
                "status",
                "started_at",
                "finished_at",
                "execution_time",
                "error_message",
            ],
        )

    def test_status_e_imutavel(self) -> None:
        status = ExperimentMonitor().mark_pending("exp-001")

        with self.assertRaises(FrozenInstanceError):
            status.status = "running"

    def test_mark_pending_registra_estado_inicial(self) -> None:
        status = ExperimentMonitor().mark_pending("exp-001")

        self.assertEqual(status.experiment_id, "exp-001")
        self.assertEqual(status.status, "pending")
        self.assertIsNone(status.started_at)
        self.assertIsNone(status.finished_at)
        self.assertEqual(status.execution_time, 0.0)
        self.assertEqual(status.error_message, "")

    def test_mark_running_registra_inicio(self) -> None:
        started_at = datetime(2026, 6, 27, 10, 0, 0)
        monitor = ExperimentMonitor()

        status = monitor.mark_running("exp-001", started_at=started_at)

        self.assertEqual(status.status, "running")
        self.assertEqual(status.started_at, started_at)
        self.assertIsNone(status.finished_at)
        self.assertIs(monitor.get_status("exp-001"), status)

    def test_mark_completed_registra_fim_e_tempo(self) -> None:
        started_at = datetime(2026, 6, 27, 10, 0, 0)
        finished_at = started_at + timedelta(seconds=12)
        monitor = ExperimentMonitor()
        monitor.mark_running("exp-001", started_at=started_at)

        status = monitor.mark_completed("exp-001", finished_at=finished_at)

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.finished_at, finished_at)
        self.assertEqual(status.execution_time, 12.0)
        self.assertEqual(status.error_message, "")

    def test_mark_failed_registra_erro(self) -> None:
        started_at = datetime(2026, 6, 27, 10, 0, 0)
        finished_at = started_at + timedelta(seconds=5)
        monitor = ExperimentMonitor()
        monitor.mark_running("exp-001", started_at=started_at)

        status = monitor.mark_failed(
            "exp-001",
            "falha controlada",
            finished_at=finished_at,
        )

        self.assertEqual(status.status, "failed")
        self.assertEqual(status.execution_time, 5.0)
        self.assertEqual(status.error_message, "falha controlada")

    def test_mark_cancelled_registra_cancelamento(self) -> None:
        status = ExperimentMonitor().mark_cancelled(
            "exp-001",
            error_message="cancelado pelo usuario",
            finished_at=datetime(2026, 6, 27, 10, 0, 0),
        )

        self.assertEqual(status.status, "cancelled")
        self.assertEqual(status.execution_time, 0.0)
        self.assertEqual(status.error_message, "cancelado pelo usuario")

    def test_lista_e_limpa_status_monitorados(self) -> None:
        monitor = ExperimentMonitor()
        first = monitor.mark_pending("exp-001")
        second = monitor.mark_pending("exp-002")

        self.assertEqual(monitor.list_statuses(), (first, second))

        monitor.clear()

        self.assertEqual(monitor.list_statuses(), ())
        self.assertIsNone(monitor.get_status("exp-001"))

    def test_statuses_permitidos_permanecem_controlados(self) -> None:
        monitor = ExperimentMonitor()
        statuses = {
            monitor.mark_pending("pending").status,
            monitor.mark_running("running").status,
            monitor.mark_completed("completed").status,
            monitor.mark_failed("failed", "erro").status,
            monitor.mark_cancelled("cancelled").status,
        }

        self.assertEqual(
            statuses,
            {"pending", "running", "completed", "failed", "cancelled"},
        )

    def test_monitor_nao_executa_experimentos_ou_acessa_dashboard(self) -> None:
        source = read_source(
            Path("research/experiment_management/experiment_monitor.py")
        )
        forbidden_fragments = (
            "ResearchRunner",
            "ResearchPipeline",
            "ExperimentScheduler",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "threading",
            "multiprocessing",
            "asyncio",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_monitor_permanece_desacoplado_de_domain_e_pipeline(self) -> None:
        path = Path("research/experiment_management/experiment_monitor.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.experiment_management.experiment_scheduler",
            "threading",
            "multiprocessing",
            "asyncio",
            "alpha",
            "strategies",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
