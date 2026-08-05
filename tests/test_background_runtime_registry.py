from __future__ import annotations

import threading
import time
import unittest
from uuid import uuid4

from core.background_runtime_registry import (
    clear_background_snapshot,
    clear_runtime_resource,
    get_background_snapshot,
    get_or_create_runtime_resource,
    is_background_runtime_running,
    publish_background_snapshot,
    start_background_runtime_once,
)


class BackgroundRuntimeRegistryTest(unittest.TestCase):
    def test_compartilha_snapshot_entre_consumidores_sem_novo_ciclo(self) -> None:
        key = f"test-snapshot-{uuid4()}"
        snapshot = {"refresh_id": 42}

        publish_background_snapshot(key, snapshot)

        self.assertIs(get_background_snapshot(key), snapshot)
        clear_background_snapshot(key)
        self.assertIsNone(get_background_snapshot(key))

    def test_nao_inicia_thread_duplicada_com_mesmo_nome(self) -> None:
        name = f"test-runtime-{uuid4()}"
        release = threading.Event()

        self.assertTrue(start_background_runtime_once(name, release.wait))
        self.assertTrue(is_background_runtime_running(name))
        self.assertFalse(start_background_runtime_once(name, release.wait))

        release.set()
        deadline = time.monotonic() + 1.0
        while is_background_runtime_running(name) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(is_background_runtime_running(name))

    def test_compartilha_recurso_pesado_e_permite_descartar(self) -> None:
        key = f"test-resource-{uuid4()}"
        created: list[object] = []

        def factory() -> object:
            resource = object()
            created.append(resource)
            return resource

        first = get_or_create_runtime_resource(key, factory)
        second = get_or_create_runtime_resource(key, factory)

        self.assertIs(first, second)
        self.assertEqual(len(created), 1)
        self.assertIs(clear_runtime_resource(key), first)
        self.assertIsNot(get_or_create_runtime_resource(key, factory), first)
        clear_runtime_resource(key)


if __name__ == "__main__":
    unittest.main()
