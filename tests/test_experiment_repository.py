"""Testes do repositorio de experimentos do Research Lab."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from research.experiment_repository import ExperimentRepository
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentRepositoryTest(unittest.TestCase):
    """Valida armazenamento em memoria de experimentos."""

    def test_save_e_get_por_experiment_id(self) -> None:
        repository = ExperimentRepository()
        experiment = _Experiment(experiment_id="exp-001", name="Alpha 001")

        saved = repository.save(experiment)

        self.assertIs(saved, experiment)
        self.assertIs(repository.get("exp-001"), experiment)

    def test_save_aceita_campo_id_como_identificador(self) -> None:
        repository = ExperimentRepository()
        experiment = _LegacyExperiment(id="legacy-001")

        repository.save(experiment)

        self.assertIs(repository.get("legacy-001"), experiment)

    def test_save_substitui_experimento_com_mesmo_id(self) -> None:
        repository = ExperimentRepository()
        first = _Experiment(experiment_id="exp-001", name="Primeiro")
        second = _Experiment(experiment_id="exp-001", name="Segundo")

        repository.save(first)
        repository.save(second)

        self.assertIs(repository.get("exp-001"), second)
        self.assertEqual(repository.list(), (second,))

    def test_list_retorna_experimentos_em_memoria(self) -> None:
        repository = ExperimentRepository()
        first = _Experiment(experiment_id="exp-001", name="A")
        second = _Experiment(experiment_id="exp-002", name="B")

        repository.save(first)
        repository.save(second)

        self.assertEqual(repository.list(), (first, second))

    def test_exists_indica_presenca_do_experimento(self) -> None:
        repository = ExperimentRepository()

        self.assertFalse(repository.exists("exp-001"))
        repository.save(_Experiment(experiment_id="exp-001", name="Alpha"))

        self.assertTrue(repository.exists("exp-001"))

    def test_delete_remove_experimento_existente(self) -> None:
        repository = ExperimentRepository()
        repository.save(_Experiment(experiment_id="exp-001", name="Alpha"))

        deleted = repository.delete("exp-001")

        self.assertTrue(deleted)
        self.assertFalse(repository.exists("exp-001"))
        self.assertIsNone(repository.get("exp-001"))

    def test_delete_retorna_false_para_id_inexistente(self) -> None:
        repository = ExperimentRepository()

        self.assertFalse(repository.delete("missing"))

    def test_save_rejeita_experimento_sem_identificador(self) -> None:
        repository = ExperimentRepository()

        with self.assertRaises(ValueError):
            repository.save(object())

    def test_repositorios_mantem_armazenamento_independente(self) -> None:
        first_repository = ExperimentRepository()
        second_repository = ExperimentRepository()

        first_repository.save(_Experiment(experiment_id="exp-001", name="Alpha"))

        self.assertTrue(first_repository.exists("exp-001"))
        self.assertFalse(second_repository.exists("exp-001"))

    def test_nao_utiliza_persistencia_externa_ou_apis(self) -> None:
        source = read_source(Path("research/experiment_repository.py"))
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
            "json",
            "pickle",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_repositorio_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/experiment_repository.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
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
class _Experiment:
    """Experimento de teste com identificador oficial."""

    experiment_id: str
    name: str


@dataclass(frozen=True)
class _LegacyExperiment:
    """Experimento de teste com identificador alternativo."""

    id: str


if __name__ == "__main__":
    unittest.main()
