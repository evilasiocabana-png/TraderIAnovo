"""Testes do versionador de experimentos do Research Lab."""

from dataclasses import FrozenInstanceError, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.experiment_version_manager import (
    ExperimentVersion,
    ExperimentVersionManager,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentVersionManagerTest(unittest.TestCase):
    """Valida criacao de versoes sem persistencia."""

    def test_experiment_version_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentVersion))
        self.assertTrue(ExperimentVersion.__dataclass_params__.frozen)

    def test_create_version_gera_metadados_da_versao(self) -> None:
        version = ExperimentVersionManager().create_version(
            experiment_id="exp-001",
            configuration={"risk": 1, "window": 5},
        )

        self.assertEqual(version.experiment_id, "exp-001")
        self.assertEqual(version.version, 1)
        self.assertIsInstance(version.created_at, datetime)
        self.assertEqual(len(version.configuration_hash), 64)

    def test_create_version_incrementa_a_partir_da_versao_atual(self) -> None:
        version = ExperimentVersionManager().create_version(
            experiment_id="exp-001",
            configuration={"risk": 1},
            current_version=3,
        )

        self.assertEqual(version.version, 4)

    def test_current_version_retorna_zero_quando_nao_ha_versao(self) -> None:
        manager = ExperimentVersionManager()

        self.assertEqual(manager.current_version(None), 0)

    def test_current_version_retorna_numero_da_versao(self) -> None:
        version = ExperimentVersion(
            experiment_id="exp-001",
            version=7,
            created_at=datetime(2026, 6, 27, 20, 50, 0),
            configuration_hash="abc",
        )

        self.assertEqual(ExperimentVersionManager().current_version(version), 7)

    def test_next_version_retorna_um_sem_versao_atual(self) -> None:
        self.assertEqual(ExperimentVersionManager().next_version(), 1)

    def test_next_version_incrementa_valor_atual(self) -> None:
        self.assertEqual(ExperimentVersionManager().next_version(10), 11)

    def test_hash_e_deterministico_para_dicts_equivalentes(self) -> None:
        manager = ExperimentVersionManager()
        first = manager.create_version(
            "exp-001",
            {"window": 5, "risk": 1},
        )
        second = manager.create_version(
            "exp-001",
            {"risk": 1, "window": 5},
        )

        self.assertEqual(first.configuration_hash, second.configuration_hash)

    def test_hash_suporta_dataclass_de_configuracao(self) -> None:
        manager = ExperimentVersionManager()

        first = manager.create_version("exp-001", _Config(risk=1, window=5))
        second = manager.create_version("exp-001", _Config(risk=1, window=5))

        self.assertEqual(first.configuration_hash, second.configuration_hash)

    def test_hash_muda_quando_configuracao_muda(self) -> None:
        manager = ExperimentVersionManager()
        first = manager.create_version("exp-001", {"risk": 1})
        second = manager.create_version("exp-001", {"risk": 2})

        self.assertNotEqual(first.configuration_hash, second.configuration_hash)

    def test_experiment_version_e_imutavel(self) -> None:
        version = ExperimentVersionManager().create_version(
            "exp-001",
            {"risk": 1},
        )

        with self.assertRaises(FrozenInstanceError):
            version.version = 2

    def test_nao_persiste_dados_nem_acessa_banco(self) -> None:
        source = read_source(Path("research/experiment_version_manager.py"))
        forbidden_fragments = (
            "sqlite",
            "SQLite",
            "postgres",
            "PostgreSQL",
            "redis",
            "requests",
            "urllib",
            "open(",
            ".write(",
            "Path(",
            "pickle",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_manager_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/experiment_version_manager.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.experiment_repository",
            "database",
            "sqlite3",
            "redis",
            "requests",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "write",
            "connect",
            "execute",
            "run",
            "calculate",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


@dataclass(frozen=True)
class _Config:
    """Configuracao de teste."""

    risk: int
    window: int


if __name__ == "__main__":
    unittest.main()
