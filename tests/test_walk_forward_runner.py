"""Testes do Walk-Forward Runner da Alpha001."""

import ast
import unittest
from pathlib import Path

from domain.candle import Candle
from research.walk_forward_runner import WalkForwardResult, WalkForwardRunner


class WalkForwardRunnerTest(unittest.TestCase):
    """Valida walk-forward sem recalibrar Alpha001."""

    def test_executa_treino(self) -> None:
        """Resultado deve conter execucao de treino."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._winning_candles(),
        )

        self.assertEqual(result.train_result["experiment_name"], "walk_forward_train")
        self.assertIn("metrics", result.train_result)

    def test_executa_teste(self) -> None:
        """Resultado deve conter execucao de teste."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._winning_candles(),
        )

        self.assertEqual(result.test_result["experiment_name"], "walk_forward_test")
        self.assertIn("metrics", result.test_result)

    def test_calcula_overfitting_score(self) -> None:
        """Score deve refletir degradacao relativa."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._flat_candles(),
        )

        self.assertIsInstance(result.overfitting_score, float)
        self.assertGreater(result.overfitting_score, 0.0)

    def test_detecta_degradacao_entre_treino_e_teste(self) -> None:
        """Teste fraco apos treino bom deve sinalizar overfitting."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._flat_candles(),
        )

        self.assertIn(result.robustness_status, {"DEGRADED", "OVERFITTED"})

    def test_retorna_walk_forward_result(self) -> None:
        """Runner deve retornar DTO de walk-forward."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._winning_candles(),
        )

        self.assertIsInstance(result, WalkForwardResult)

    def test_mesma_configuracao_em_treino_e_teste(self) -> None:
        """Stop e target nao devem mudar entre treino e teste."""
        result = WalkForwardRunner(stop_points=35.0, target_points=70.0).run(
            self._winning_candles(),
            self._winning_candles(),
        )

        train_config = result.train_result["configuration"]
        test_config = result.test_result["configuration"]
        self.assertEqual(train_config["stop_points"], test_config["stop_points"])
        self.assertEqual(train_config["target_points"], test_config["target_points"])
        self.assertEqual(train_config["stop_points"], 35.0)
        self.assertEqual(train_config["target_points"], 70.0)

    def test_status_robust_quando_teste_preserva_resultado(self) -> None:
        """Sem degradacao relevante, status deve ser ROBUST."""
        result = WalkForwardRunner().run(
            self._winning_candles(),
            self._winning_candles(),
        )

        self.assertEqual(result.robustness_status, "ROBUST")
        self.assertEqual(result.overfitting_score, 0.0)

    def test_nao_importa_broker_replay_ou_strategy_diretamente(self) -> None:
        """Runner deve orquestrar componentes existentes."""
        imports = self._imports(Path("research/walk_forward_runner.py"))

        self.assertNotIn("core.broker", imports)
        self.assertNotIn("application.replay_service", imports)
        self.assertNotIn("strategies.alpha001_iorb_strategy", imports)

    def _winning_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0),
            self._candle("09:05", 105.0, 118.0, 98.0),
            self._candle("09:16", 126.0, 128.0, 121.0),
            self._candle("09:17", 226.0, 230.0, 126.0),
        ]

    def _flat_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0),
            self._candle("09:05", 105.0, 118.0, 98.0),
            self._candle("09:16", 110.0, 116.0, 100.0),
            self._candle("09:17", 111.0, 117.0, 101.0),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=1500,
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
