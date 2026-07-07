"""Testes do agendador oficial de experimentos."""

from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_queue import ExperimentQueue
from research.experiment_management.experiment_scheduler import ExperimentScheduler
from research.research_stage import ResearchStage
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentSchedulerTest(unittest.TestCase):
    """Valida agendamento sequencial sem paralelismo."""

    def test_run_next_retorna_none_quando_fila_esta_vazia(self) -> None:
        scheduler = ExperimentScheduler(
            queue=ExperimentQueue(),
            runner=_RunnerSpy([]),
            experiment_factory=_ExperimentFactorySpy([]),
        )

        self.assertIsNone(scheduler.run_next())
        self.assertEqual(scheduler.processed(), ())

    def test_run_next_consumindo_fila_delega_ao_runner(self) -> None:
        calls: list[str] = []
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))
        runner = _RunnerSpy(calls)
        factory = _ExperimentFactorySpy(calls)
        scheduler = ExperimentScheduler(queue, runner, factory)

        result = scheduler.run_next()

        self.assertEqual(calls, ["factory:RUNNING", "runner"])
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.experiment_id, "exp-001")
        self.assertEqual(queue.size(), 0)
        self.assertEqual(scheduler.processed(), (result,))
        self.assertIs(runner.experiment, factory.experiment)

    def test_run_all_executa_um_experimento_por_vez_em_ordem_fifo(self) -> None:
        calls: list[str] = []
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))
        queue.enqueue(self._definition("exp-002"))

        results = ExperimentScheduler(
            queue=queue,
            runner=_RunnerSpy(calls),
            experiment_factory=_ExperimentFactorySpy(calls),
        ).run_all()

        self.assertEqual(
            calls,
            [
                "factory:RUNNING",
                "runner",
                "factory:RUNNING",
                "runner",
            ],
        )
        self.assertEqual([item.experiment_id for item in results], ["exp-001", "exp-002"])
        self.assertEqual([item.status for item in results], ["COMPLETED", "COMPLETED"])
        self.assertEqual(queue.size(), 0)

    def test_scheduler_marca_failed_quando_runner_retorna_erro(self) -> None:
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))

        result = ExperimentScheduler(
            queue=queue,
            runner=_RunnerSpy([], status=ResearchStage.FAILED, errors=("falha",)),
            experiment_factory=_ExperimentFactorySpy([]),
        ).run_next()

        self.assertEqual(result.status, "FAILED")

    def test_scheduler_marca_failed_quando_factory_falha(self) -> None:
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))

        result = ExperimentScheduler(
            queue=queue,
            runner=_RunnerSpy([]),
            experiment_factory=_FailingFactory(),
        ).run_next()

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(queue.size(), 0)

    def test_scheduler_preserva_definition_original_imutavel(self) -> None:
        queue = ExperimentQueue()
        definition = self._definition("exp-001")
        queue.enqueue(definition)

        result = ExperimentScheduler(
            queue=queue,
            runner=_RunnerSpy([]),
            experiment_factory=_ExperimentFactorySpy([]),
        ).run_next()

        self.assertEqual(definition.status, "PENDING")
        self.assertEqual(result.status, "COMPLETED")
        self.assertIsNot(result, definition)

    def test_scheduler_nao_usa_threads_processos_asyncio_ou_operacao(self) -> None:
        source = read_source(
            Path("research/experiment_management/experiment_scheduler.py")
        )
        forbidden_fragments = (
            "threading",
            "multiprocessing",
            "asyncio",
            "Thread(",
            "Process(",
            "Pool(",
            "create_task",
            "gather(",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_scheduler_permanece_desacoplado_de_domain_pipeline_e_operacao(self) -> None:
        path = Path("research/experiment_management/experiment_scheduler.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
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
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.research_runner", imports)

    def _definition(self, experiment_id: str) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha002",
            alpha_version="0.1.0",
            configuration_version="cfg-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            status="PENDING",
            priority=1,
            created_at="2026-06-27T23:40:00-03:00",
            metadata={"source": "test"},
        )


class _RunnerResult:
    def __init__(
        self,
        status: ResearchStage = ResearchStage.COMPLETED,
        errors: tuple[str, ...] = (),
    ) -> None:
        self.status = status
        self.errors = errors


class _RunnerSpy:
    def __init__(
        self,
        calls: list[str],
        status: ResearchStage = ResearchStage.COMPLETED,
        errors: tuple[str, ...] = (),
    ) -> None:
        self.calls = calls
        self.status = status
        self.errors = errors
        self.experiment: object | None = None

    def run(self, experiment: object) -> _RunnerResult:
        self.calls.append("runner")
        self.experiment = experiment
        return _RunnerResult(self.status, self.errors)


class _ExperimentFactorySpy:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.experiment = object()

    def __call__(self, definition: ExperimentDefinition) -> object:
        self.calls.append(f"factory:{definition.status}")
        return self.experiment


class _FailingFactory:
    def __call__(self, definition: ExperimentDefinition) -> object:
        raise RuntimeError("falha controlada")


if __name__ == "__main__":
    unittest.main()
