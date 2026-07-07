"""Testes do batch runner historico da Alpha001."""

import ast
import unittest
from pathlib import Path

from domain.candle import Candle
from research.historical_batch_runner import (
    HistoricalBatchResult,
    HistoricalBatchRunner,
    HistoricalDataset,
)


class HistoricalBatchRunnerTest(unittest.TestCase):
    """Valida execucao da Alpha001 em multiplos datasets historicos."""

    def test_executa_multiplos_datasets(self) -> None:
        """Runner deve executar todos os datasets recebidos."""
        result = HistoricalBatchRunner().run(
            [
                HistoricalDataset("dataset_buy", self._buy_candles()),
                HistoricalDataset("dataset_sell", self._sell_candles()),
            ]
        )

        self.assertEqual(result.total_datasets, 2)
        self.assertEqual(result.datasets_executed, 2)

    def test_gera_um_resultado_por_dataset(self) -> None:
        """Cada dataset deve gerar uma entrada de resultado."""
        result = HistoricalBatchRunner().run(
            [
                HistoricalDataset("dataset_buy", self._buy_candles()),
                HistoricalDataset("dataset_empty", []),
            ]
        )

        self.assertEqual(len(result.results), 2)
        self.assertEqual(result.results[0]["experiment_name"], "dataset_buy")

    def test_consolida_resumo_final(self) -> None:
        """Resumo deve conter aprovados e rejeitados."""
        result = HistoricalBatchRunner().run(
            [
                HistoricalDataset("dataset_buy", self._buy_candles()),
                HistoricalDataset("dataset_empty", []),
            ]
        )

        self.assertEqual(result.approved, 1)
        self.assertEqual(result.rejected, 1)
        self.assertIn("dataset(s) historico(s)", result.summary)

    def test_retorna_melhor_dataset(self) -> None:
        """Melhor dataset deve vir do maior lucro liquido."""
        result = HistoricalBatchRunner().run(
            [
                HistoricalDataset("dataset_buy", self._buy_candles()),
                HistoricalDataset("dataset_empty", []),
            ]
        )

        self.assertEqual(result.best_dataset, "dataset_buy")

    def test_aceita_datasets_em_dict(self) -> None:
        """Runner deve aceitar datasets ja carregados em dict."""
        result = HistoricalBatchRunner().run(
            [
                {"name": "dict_dataset", "candles": self._buy_candles()},
            ]
        )

        self.assertEqual(result.total_datasets, 1)
        self.assertEqual(result.results[0]["experiment_name"], "dict_dataset")

    def test_aceita_lista_de_candles(self) -> None:
        """Runner deve aceitar uma lista de Candle como dataset anonimo."""
        result = HistoricalBatchRunner().run([self._buy_candles()])

        self.assertEqual(result.results[0]["experiment_name"], "dataset_1")

    def test_resultado_tem_resumo_estatistico(self) -> None:
        """Batch deve repassar resumo estatistico do runner Alpha001."""
        result = HistoricalBatchRunner().run(
            [HistoricalDataset("dataset_buy", self._buy_candles())]
        )

        self.assertIn("average_net_profit_points", result.statistical_summary)
        self.assertIn("best_net_profit_points", result.statistical_summary)

    def test_retorna_historical_batch_result(self) -> None:
        """Runner deve retornar DTO consolidado."""
        result = HistoricalBatchRunner().run([])

        self.assertIsInstance(result, HistoricalBatchResult)
        self.assertEqual(result.total_datasets, 0)
        self.assertEqual(result.results, [])

    def test_nao_importa_csv_ou_loader_diretamente(self) -> None:
        """Batch runner nao deve duplicar importacao historica."""
        imports = self._imports(Path("research/historical_batch_runner.py"))
        source = Path("research/historical_batch_runner.py").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("csv", imports)
        self.assertNotIn("data.historical_data_loader", imports)
        self.assertNotIn("HistoricalDataLoader", source)

    def test_nao_importa_broker_ou_replay_diretamente(self) -> None:
        """Batch runner deve orquestrar via componentes existentes."""
        imports = self._imports(Path("research/historical_batch_runner.py"))

        self.assertNotIn("core.broker", imports)
        self.assertNotIn("application.replay_service", imports)

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
            self._candle("09:17", 226.0, 230.0, 126.0, 1500),
        ]

    def _sell_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 110.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 94.0, 99.0, 92.0, 1500),
            self._candle("09:17", -6.0, 94.0, -10.0, 1500),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
        volume: int,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=volume,
        )

    def _imports(self, caminho: Path) -> set[str]:
        tree = ast.parse(caminho.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
