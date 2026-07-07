"""Testes do repositorio de features."""

import unittest

from market.feature_engine import FeatureSnapshot
from market.feature_store import FeatureStore


class FeatureStoreTest(unittest.TestCase):
    """Valida armazenamento isolado do ultimo snapshot de features."""

    def test_store_e_latest_retornam_ultimo_snapshot(self) -> None:
        """Garante armazenamento e leitura do snapshot atual."""
        store = FeatureStore()
        snapshot = self._snapshot(momentum=10)

        store.store(snapshot)

        self.assertEqual(store.latest(), snapshot)

    def test_store_substitui_snapshot_anterior(self) -> None:
        """Garante que apenas o ultimo snapshot fica armazenado."""
        store = FeatureStore()
        store.store(self._snapshot(momentum=10))
        latest_snapshot = self._snapshot(momentum=20)

        store.store(latest_snapshot)

        self.assertEqual(store.latest(), latest_snapshot)

    def test_clear_remove_snapshot_atual(self) -> None:
        """Garante limpeza do store."""
        store = FeatureStore()
        store.store(self._snapshot(momentum=10))

        store.clear()

        self.assertIsNone(store.latest())

    def test_has_feature_identifica_feature_existente(self) -> None:
        """Garante verificacao de feature por nome."""
        store = FeatureStore()
        store.store(self._snapshot(momentum=10))

        self.assertTrue(store.has_feature("momentum"))
        self.assertFalse(store.has_feature("inexistente"))

    def test_get_retorna_valor_da_feature(self) -> None:
        """Garante leitura de valor por nome."""
        store = FeatureStore()
        store.store(self._snapshot(momentum=10))

        self.assertEqual(store.get("momentum"), 10)
        self.assertEqual(store.get("direction"), "UP")

    def test_get_e_has_feature_sem_snapshot_retornam_fallback(self) -> None:
        """Garante fallback quando nao ha snapshot."""
        store = FeatureStore()

        self.assertIsNone(store.get("momentum"))
        self.assertFalse(store.has_feature("momentum"))

    def test_list_features_retorna_nomes_disponiveis(self) -> None:
        """Garante listagem de features do snapshot."""
        store = FeatureStore()
        store.store(self._snapshot(momentum=10))

        features = store.list_features()

        self.assertIn("momentum", features)
        self.assertIn("average_range", features)
        self.assertIn("volatility_level", features)

    def test_list_features_sem_snapshot_retorna_lista_vazia(self) -> None:
        """Garante listagem vazia sem snapshot."""
        self.assertEqual(FeatureStore().list_features(), [])

    def _snapshot(self, momentum: float) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=momentum,
            average_range=10,
            highest_high=120,
            lowest_low=90,
            direction="UP",
            candles_count=2,
            trend_strength=1.0,
            volatility_level="MEDIUM",
        )


if __name__ == "__main__":
    unittest.main()
