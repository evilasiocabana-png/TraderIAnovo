"""Testes do repositorio de resultados do Research Pipeline."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from research.research_result_repository import ResearchResultRepository
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchResultRepositoryTest(unittest.TestCase):
    """Valida armazenamento em memoria de ResearchExecutionResult."""

    def test_save_e_get_por_execution_id(self) -> None:
        repository = ResearchResultRepository()
        result = _ExecutionResult(
            execution_id="exec-001",
            experiment_id="exp-001",
        )

        saved = repository.save(result)

        self.assertIs(saved, result)
        self.assertIs(repository.get("exec-001"), result)

    def test_save_aceita_id_como_identificador_alternativo(self) -> None:
        repository = ResearchResultRepository()
        result = _LegacyExecutionResult(id="legacy-001", experiment_id="exp-001")

        repository.save(result)

        self.assertIs(repository.get("legacy-001"), result)

    def test_save_substitui_resultado_com_mesmo_execution_id(self) -> None:
        repository = ResearchResultRepository()
        first = _ExecutionResult("exec-001", "exp-001")
        second = _ExecutionResult("exec-001", "exp-002")

        repository.save(first)
        repository.save(second)

        self.assertIs(repository.get("exec-001"), second)
        self.assertEqual(repository.list(), (second,))

    def test_list_retorna_resultados_em_memoria(self) -> None:
        repository = ResearchResultRepository()
        first = _ExecutionResult("exec-001", "exp-001")
        second = _ExecutionResult("exec-002", "exp-002")

        repository.save(first)
        repository.save(second)

        self.assertEqual(repository.list(), (first, second))

    def test_delete_remove_resultado_existente(self) -> None:
        repository = ResearchResultRepository()
        repository.save(_ExecutionResult("exec-001", "exp-001"))

        deleted = repository.delete("exec-001")

        self.assertTrue(deleted)
        self.assertIsNone(repository.get("exec-001"))

    def test_delete_retorna_false_para_id_inexistente(self) -> None:
        repository = ResearchResultRepository()

        self.assertFalse(repository.delete("missing"))

    def test_list_by_experiment_filtra_por_experiment_id(self) -> None:
        repository = ResearchResultRepository()
        first = _ExecutionResult("exec-001", "exp-001")
        second = _ExecutionResult("exec-002", "exp-002")
        third = _ExecutionResult("exec-003", "exp-001")

        repository.save(first)
        repository.save(second)
        repository.save(third)

        self.assertEqual(repository.list_by_experiment("exp-001"), (first, third))
        self.assertEqual(repository.list_by_experiment("exp-002"), (second,))

    def test_list_by_experiment_tambem_ler_id_do_experiment_aninhado(self) -> None:
        repository = ResearchResultRepository()
        result = _NestedExecutionResult(
            execution_id="exec-001",
            experiment=_Experiment(experiment_id="exp-001"),
        )

        repository.save(result)

        self.assertEqual(repository.list_by_experiment("exp-001"), (result,))

    def test_save_rejeita_resultado_sem_identificador(self) -> None:
        repository = ResearchResultRepository()

        with self.assertRaises(ValueError):
            repository.save(object())

    def test_repositorios_mantem_armazenamento_independente(self) -> None:
        first_repository = ResearchResultRepository()
        second_repository = ResearchResultRepository()

        first_repository.save(_ExecutionResult("exec-001", "exp-001"))

        self.assertIsNotNone(first_repository.get("exec-001"))
        self.assertIsNone(second_repository.get("exec-001"))

    def test_nao_utiliza_persistencia_externa(self) -> None:
        source = read_source(Path("research/research_result_repository.py"))
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
        path = Path("research/research_result_repository.py")
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
class _ExecutionResult:
    """Resultado de execucao com identificadores oficiais."""

    execution_id: str
    experiment_id: str


@dataclass(frozen=True)
class _LegacyExecutionResult:
    """Resultado de execucao com identificador alternativo."""

    id: str
    experiment_id: str


@dataclass(frozen=True)
class _NestedExecutionResult:
    """Resultado de execucao com experimento aninhado."""

    execution_id: str
    experiment: object


@dataclass(frozen=True)
class _Experiment:
    """Experimento aninhado usado para filtro."""

    experiment_id: str


if __name__ == "__main__":
    unittest.main()
