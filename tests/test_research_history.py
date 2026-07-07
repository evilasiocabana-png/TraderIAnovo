"""Testes do historico oficial de pesquisas."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.research_history import ResearchHistory
from research.research_result_repository import ResearchResultRepository
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchHistoryTest(unittest.TestCase):
    """Valida consultas sobre resultados de pesquisa existentes."""

    def test_list_all_retorna_todos_os_resultados(self) -> None:
        repository = ResearchResultRepository()
        first = _ResearchResult("exec-001", "Alpha001", 1)
        second = _ResearchResult("exec-002", "Alpha002", 1)
        repository.save(first)
        repository.save(second)

        self.assertEqual(ResearchHistory(repository).list_all(), (first, second))

    def test_list_by_alpha_filtra_pelo_nome_da_alpha(self) -> None:
        repository = ResearchResultRepository()
        alpha001 = _ResearchResult("exec-001", "Alpha001", 1)
        alpha002 = _ResearchResult("exec-002", "Alpha002", 1)
        repository.save(alpha001)
        repository.save(alpha002)

        self.assertEqual(
            ResearchHistory(repository).list_by_alpha("Alpha001"),
            (alpha001,),
        )

    def test_list_by_alpha_ler_alpha_do_experimento_aninhado(self) -> None:
        repository = ResearchResultRepository()
        result = _NestedResearchResult(
            execution_id="exec-001",
            experiment=_Experiment(alpha_id="Alpha001", version=1),
            started_at=datetime(2026, 6, 27, 20, 0, 0),
        )
        repository.save(result)

        self.assertEqual(
            ResearchHistory(repository).list_by_alpha("Alpha001"),
            (result,),
        )

    def test_list_by_version_filtra_por_versao(self) -> None:
        repository = ResearchResultRepository()
        version_1 = _ResearchResult("exec-001", "Alpha001", 1)
        version_2 = _ResearchResult("exec-002", "Alpha001", 2)
        repository.save(version_1)
        repository.save(version_2)

        self.assertEqual(
            ResearchHistory(repository).list_by_version(2),
            (version_2,),
        )

    def test_list_by_period_filtra_por_started_at(self) -> None:
        repository = ResearchResultRepository()
        before = _ResearchResult(
            "exec-001",
            "Alpha001",
            1,
            started_at=datetime(2026, 6, 26, 20, 0, 0),
        )
        inside = _ResearchResult(
            "exec-002",
            "Alpha001",
            1,
            started_at=datetime(2026, 6, 27, 20, 0, 0),
        )
        after = _ResearchResult(
            "exec-003",
            "Alpha001",
            1,
            started_at=datetime(2026, 6, 28, 20, 0, 0),
        )
        repository.save(before)
        repository.save(inside)
        repository.save(after)

        self.assertEqual(
            ResearchHistory(repository).list_by_period(
                datetime(2026, 6, 27, 0, 0, 0),
                datetime(2026, 6, 27, 23, 59, 59),
            ),
            (inside,),
        )

    def test_latest_retorna_resultado_mais_recente(self) -> None:
        repository = ResearchResultRepository()
        older = _ResearchResult(
            "exec-001",
            "Alpha001",
            1,
            started_at=datetime(2026, 6, 27, 20, 0, 0),
        )
        newer = _ResearchResult(
            "exec-002",
            "Alpha001",
            1,
            started_at=datetime(2026, 6, 27, 21, 0, 0),
        )
        repository.save(older)
        repository.save(newer)

        self.assertIs(ResearchHistory(repository).latest(), newer)

    def test_latest_retorna_none_sem_resultados(self) -> None:
        self.assertIsNone(ResearchHistory().latest())

    def test_history_nao_executa_pesquisas_ou_calculos(self) -> None:
        source = read_source(Path("research/research_history.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "Alpha001Experiment",
            "ResearchRunner(",
            "ResearchPipeline(",
            "sum(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_history_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/research_history.py")
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
class _ResearchResult:
    """Resultado de pesquisa usado pelo historico."""

    execution_id: str
    alpha: str
    version: int
    started_at: datetime = datetime(2026, 6, 27, 20, 0, 0)


@dataclass(frozen=True)
class _NestedResearchResult:
    """Resultado com experimento aninhado."""

    execution_id: str
    experiment: object
    started_at: datetime


@dataclass(frozen=True)
class _Experiment:
    """Experimento aninhado com metadados de pesquisa."""

    alpha_id: str
    version: int


if __name__ == "__main__":
    unittest.main()
