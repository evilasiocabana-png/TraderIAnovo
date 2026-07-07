"""Testes do motor Walk-Forward estrutural da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_walk_forward_engine import (
    Alpha001WalkForwardEngine,
    Alpha001WalkForwardMetrics,
    Alpha001WalkForwardResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001WalkForwardEngineTest(unittest.TestCase):
    """Valida agrupamento Walk-Forward sem executar experimentos."""

    def test_resultados_sao_dataclasses_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001WalkForwardResult))
        self.assertTrue(Alpha001WalkForwardResult.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(Alpha001WalkForwardMetrics))
        self.assertTrue(Alpha001WalkForwardMetrics.__dataclass_params__.frozen)

    def test_calcula_metricas_por_janelas_configuradas(self) -> None:
        result = Alpha001WalkForwardEngine(
            training_window=2,
            validation_window=1,
            testing_window=1,
        ).calculate(
            [
                self._experiment(10, 2, 1, 7),
                self._experiment(20, 3, 2, 15),
                self._experiment(30, 4, 3, 23),
                self._experiment(40, 5, 4, 31),
            ],
        )

        self.assertEqual(result.training_window, 2)
        self.assertEqual(result.validation_window, 1)
        self.assertEqual(result.testing_window, 1)
        self.assertEqual(result.training_metrics.total_experiments, 2)
        self.assertEqual(result.training_metrics.total_candles, 30)
        self.assertEqual(result.training_metrics.total_buy, 5)
        self.assertEqual(result.training_metrics.total_sell, 3)
        self.assertEqual(result.training_metrics.total_wait, 22)
        self.assertEqual(result.validation_metrics.total_candles, 30)
        self.assertEqual(result.testing_metrics.total_candles, 40)

    def test_janelas_incompletas_retornam_metricas_disponiveis(self) -> None:
        result = Alpha001WalkForwardEngine(
            training_window=2,
            validation_window=2,
            testing_window=2,
        ).calculate([self._experiment(10, 1, 1, 8)])

        self.assertEqual(result.training_metrics.total_experiments, 1)
        self.assertEqual(result.validation_metrics.total_experiments, 0)
        self.assertEqual(result.testing_metrics.total_experiments, 0)
        self.assertEqual(result.validation_metrics.total_candles, 0)
        self.assertEqual(result.testing_metrics.total_signals, 0)

    def test_colecao_vazia_retorna_metricas_zero(self) -> None:
        result = Alpha001WalkForwardEngine(
            training_window=1,
            validation_window=1,
            testing_window=1,
        ).calculate([])

        self.assertEqual(result.training_metrics.total_experiments, 0)
        self.assertEqual(result.validation_metrics.total_experiments, 0)
        self.assertEqual(result.testing_metrics.total_experiments, 0)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001WalkForwardEngine(
            training_window=1,
            validation_window=1,
            testing_window=1,
        ).calculate([])

        with self.assertRaises(FrozenInstanceError):
            result.training_window = 2

    def test_engine_nao_otimiza_parametros_ou_executa_experimentos(self) -> None:
        source = read_source(Path("research/alpha001_walk_forward_engine.py"))
        forbidden_fragments = (
            "Alpha001Experiment(",
            "Alpha001Config(",
            "Alpha001ParameterSweep",
            "optimize",
            "optimizer",
            "best_parameters",
            "select_parameters",
            "Machine Learning",
            "machine_learning",
            "sklearn",
            "openai",
            "AI",
            "IA",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("research/alpha001_walk_forward_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
            "alpha",
            "strategies",
        }
        forbidden_calls = {
            "open",
            "write",
            "run",
            "generate_signal",
            "order_send",
            "execute_order",
            "next_candle",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _experiment(
        self,
        total_candles: int,
        total_buy: int,
        total_sell: int,
        total_wait: int,
    ) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=total_candles,
            total_signals=total_buy + total_sell + total_wait,
            total_buy=total_buy,
            total_sell=total_sell,
            total_wait=total_wait,
            execution_time_ms=1.0,
            signals=(),
        )


if __name__ == "__main__":
    unittest.main()
