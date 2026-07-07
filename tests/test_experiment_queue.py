"""Testes da fila oficial de experimentos do Research Lab."""

from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_queue import ExperimentQueue
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentQueueTest(unittest.TestCase):
    """Valida fila em memoria sem execucao ou paralelismo."""

    def test_fila_inicia_vazia(self) -> None:
        queue = ExperimentQueue()

        self.assertEqual(queue.size(), 0)
        self.assertIsNone(queue.peek())
        self.assertIsNone(queue.dequeue())

    def test_enqueue_adiciona_e_retorna_experimento(self) -> None:
        queue = ExperimentQueue()
        experiment = self._definition("exp-001")

        returned = queue.enqueue(experiment)

        self.assertIs(returned, experiment)
        self.assertEqual(queue.size(), 1)
        self.assertIs(queue.peek(), experiment)

    def test_dequeue_remove_em_ordem_fifo(self) -> None:
        queue = ExperimentQueue()
        first = self._definition("exp-001")
        second = self._definition("exp-002")
        queue.enqueue(first)
        queue.enqueue(second)

        self.assertIs(queue.dequeue(), first)
        self.assertIs(queue.dequeue(), second)
        self.assertIsNone(queue.dequeue())
        self.assertEqual(queue.size(), 0)

    def test_peek_nao_remove_experimento(self) -> None:
        queue = ExperimentQueue()
        experiment = self._definition("exp-001")
        queue.enqueue(experiment)

        self.assertIs(queue.peek(), experiment)
        self.assertIs(queue.peek(), experiment)
        self.assertEqual(queue.size(), 1)

    def test_cancel_remove_experimento_por_id(self) -> None:
        queue = ExperimentQueue()
        first = self._definition("exp-001")
        second = self._definition("exp-002")
        queue.enqueue(first)
        queue.enqueue(second)

        self.assertTrue(queue.cancel("exp-001"))
        self.assertEqual(queue.size(), 1)
        self.assertIs(queue.peek(), second)

    def test_cancel_retorna_false_quando_id_nao_existe(self) -> None:
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))

        self.assertFalse(queue.cancel("exp-inexistente"))
        self.assertEqual(queue.size(), 1)

    def test_clear_esvazia_fila(self) -> None:
        queue = ExperimentQueue()
        queue.enqueue(self._definition("exp-001"))
        queue.enqueue(self._definition("exp-002"))

        queue.clear()

        self.assertEqual(queue.size(), 0)
        self.assertIsNone(queue.peek())

    def test_queue_nao_executa_experimentos_ou_usa_paralelismo(self) -> None:
        source = read_source(
            Path("research/experiment_management/experiment_queue.py")
        )
        forbidden_fragments = (
            "threading",
            "multiprocessing",
            "asyncio",
            "ResearchRunner",
            "ResearchPipeline",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_queue_permanece_desacoplada_de_operacao(self) -> None:
        path = Path("research/experiment_management/experiment_queue.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
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
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

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


if __name__ == "__main__":
    unittest.main()
