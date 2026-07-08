"""Testes do Runtime Guard de infraestrutura."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import dashboard_app
from application.runtime_guard_service import RuntimeGuardService
from core.runtime_guard import (
    MT5RuntimeQueue,
    RuntimeCleanupPolicy,
    RuntimeEventLog,
    RuntimeGuardLock,
    RuntimeScheduler,
    RuntimeStateCategory,
    RuntimeStatePreserver,
)
from core.runtime_guard.runtime_state import classify_runtime_state_key


class RuntimeGuardServiceTest(unittest.TestCase):
    def test_classifica_estado_operacional_protegido(self) -> None:
        self.assertEqual(
            classify_runtime_state_key("dashboard_service"),
            RuntimeStateCategory.OPERACIONAL_PROTEGIDO,
        )

    def test_cleanup_remove_somente_temporarios(self) -> None:
        state = {
            "runtime_temp_probe": 1,
            "mt5_forex_last_auto_load_at": 2,
            "dashboard_service": object(),
            "unknown_key": 3,
        }

        result = RuntimeCleanupPolicy().cleanup_temporary(state)

        self.assertEqual(
            set(result.removed_keys),
            {"runtime_temp_probe", "mt5_forex_last_auto_load_at"},
        )
        self.assertIn("dashboard_service", state)
        self.assertIn("unknown_key", state)

    def test_cleanup_nao_remove_operacional_protegido(self) -> None:
        state = {"mt5_demo_robot_online_enabled": True}

        result = RuntimeCleanupPolicy().cleanup_temporary(state)

        self.assertEqual(result.removed_keys, ())
        self.assertTrue(state["mt5_demo_robot_online_enabled"])

    def test_snapshot_valido_e_preservado_quando_leitura_vem_vazia(self) -> None:
        preserver = RuntimeStatePreserver()

        preserver.preserve_or_replace("forex", [1], validator=bool)
        result = preserver.preserve_or_replace("forex", [], validator=bool)

        self.assertEqual(result, [1])

    def test_snapshot_e_substituido_quando_leitura_nova_e_valida(self) -> None:
        preserver = RuntimeStatePreserver()

        preserver.preserve_or_replace("forex", [1], validator=bool)
        result = preserver.preserve_or_replace("forex", [2], validator=bool)

        self.assertEqual(result, [2])

    def test_lock_impede_duas_instancias_ativas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "runtime_lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "pid": 999999,
                        "mode": "ACTIVE",
                        "heartbeat_at": "2999-01-01T00:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            lock = RuntimeGuardLock(lock_path=lock_path, stale_after_seconds=90)
            lock._service._pid_alive = lambda pid: True  # type: ignore[method-assign]

            result = lock.acquire_active()

            self.assertFalse(result.acquired)

    def test_lock_stale_pode_ser_limpo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "runtime_lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "pid": 999999,
                        "mode": "ACTIVE",
                        "heartbeat_at": "2000-01-01T00:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            lock = RuntimeGuardLock(lock_path=lock_path, stale_after_seconds=1)
            lock._service._pid_alive = lambda pid: True  # type: ignore[method-assign]

            result = lock.acquire_active()

            self.assertTrue(result.acquired)

    def test_scheduler_respeita_intervalo_minimo(self) -> None:
        scheduler = RuntimeScheduler()

        self.assertTrue(
            scheduler.should_run("forex", interval_seconds=10, now=100).allowed
        )
        scheduler.mark_run("forex", now=100)
        decision = scheduler.should_run("forex", interval_seconds=10, now=105)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "INTERVAL_NOT_REACHED")

    def test_scheduler_nao_dispara_lab_pesado_em_diagnostico(self) -> None:
        decision = RuntimeScheduler().should_run(
            "lab_heavy",
            interval_seconds=1,
            now=1,
            diagnostic_only=True,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "DIAGNOSTIC_ONLY")

    def test_diagnostico_nao_inicia_ciclo_operacional(self) -> None:
        guard = RuntimeGuardService()

        decision = guard.should_run_cycle(
            "diagnostic_only",
            interval_seconds=1,
            diagnostic_only=True,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("DIAGNOSTIC_ONLY_SKIPPED", guard.event_log.as_strings()[-1])

    def test_queue_deduplica_leituras_identicas(self) -> None:
        queue = MT5RuntimeQueue(ttl_seconds=10)

        first = queue.request(("EURUSD", "M1"), now=100)
        second = queue.request(("EURUSD", "M1"), now=105)

        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(second.reason, "DEDUPLICATED")

    def test_health_snapshot_nao_tem_side_effect(self) -> None:
        guard = RuntimeGuardService()
        before = guard.event_log.list_events()

        snapshot = guard.health_snapshot(mode="LIGHT")

        self.assertEqual(before, guard.event_log.list_events())
        self.assertEqual(snapshot.mode, "LIGHT")

    def test_event_log_respeita_limite_de_tamanho(self) -> None:
        log = RuntimeEventLog(max_size=3)

        for index in range(5):
            log.record(f"EVENT_{index}")

        self.assertEqual([event.name for event in log.list_events()], ["EVENT_2", "EVENT_3", "EVENT_4"])

    def test_dashboard_consegue_consumir_runtime_guard_service(self) -> None:
        guard = dashboard_app.get_runtime_guard_service()

        self.assertIsInstance(guard, RuntimeGuardService)
