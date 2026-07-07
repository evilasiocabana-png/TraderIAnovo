"""Testes do laboratorio quantitativo de replay."""

import unittest

from core.configuration_manager import ConfigurationManager
from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from research.benchmark_comparator import BenchmarkComparison
from research.experiment_validator import ExperimentValidation
from research.research_lab import (
    ParameterGridResult,
    ResearchExperiment,
    ResearchLab,
)
from research.strategy_benchmark import StrategyBenchmarkResult


class StaticStrategy:
    """Estrategia fixa para benchmarks do ResearchLab."""

    nome = "lab_static_buy"

    def analisar(self, estado: object) -> StrategySignal:
        """Retorna sempre compra."""
        return StrategySignal("BUY", 80, 0.8, ["Benchmark"])


class WaitStrategy:
    """Estrategia fixa sem operacoes para comparacao."""

    nome = "lab_wait"

    def analisar(self, estado: object) -> StrategySignal:
        """Retorna sempre espera."""
        return StrategySignal("WAIT", 10, 0.1, ["Benchmark"])


class ResearchLabTest(unittest.TestCase):
    """Valida experimentos quantitativos em memoria."""

    def setUp(self) -> None:
        """Restaura configuracao padrao antes de cada teste."""
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        """Evita vazamento de configuracao para outros testes."""
        ConfigurationManager.reset_configuration()

    def test_run_experiment_executa_um_replay(self) -> None:
        """Garante execucao de um replay isolado."""
        lab = ResearchLab()
        experiment = self._experiment()

        completed = lab.run_experiment(experiment)

        self.assertIsNotNone(completed.result)
        self.assertTrue(completed.result.is_finished)
        self.assertEqual(completed.result.total_candles, 2)
        self.assertEqual(completed.experiment_name, "baseline")

    def test_run_experiment_armazena_resultado_em_memoria(self) -> None:
        """Garante armazenamento do experimento executado."""
        lab = ResearchLab()

        completed = lab.run_experiment(self._experiment())

        self.assertEqual(lab.list_experiments(), [completed])

    def test_list_experiments_retorna_copia_da_lista(self) -> None:
        """Garante que a lista interna nao e exposta diretamente."""
        lab = ResearchLab()
        lab.run_experiment(self._experiment())

        experiments = lab.list_experiments()
        experiments.clear()

        self.assertEqual(len(lab.list_experiments()), 1)

    def test_last_experiment_retorna_ultimo_executado(self) -> None:
        """Garante consulta do ultimo experimento."""
        lab = ResearchLab()
        first = lab.run_experiment(self._experiment("baseline"))
        second = lab.run_experiment(self._experiment("aggressive"))

        self.assertEqual(first.experiment_name, "baseline")
        self.assertEqual(lab.last_experiment(), second)

    def test_last_experiment_retorna_none_sem_experimentos(self) -> None:
        """Garante retorno vazio quando nada foi executado."""
        self.assertIsNone(ResearchLab().last_experiment())

    def test_clear_remove_experimentos(self) -> None:
        """Garante limpeza do laboratorio em memoria."""
        lab = ResearchLab()
        lab.run_experiment(self._experiment())

        lab.clear()

        self.assertEqual(lab.list_experiments(), [])
        self.assertIsNone(lab.last_experiment())

    def test_run_experiment_restaura_configuracao_original(self) -> None:
        """Garante que configuracao global nao vaza do experimento."""
        ConfigurationManager.update_configuration(
            stop_points=30.0,
            target_points=60.0,
        )
        lab = ResearchLab()

        lab.run_experiment(
            self._experiment(stop_points=10.0, target_points=20.0)
        )
        configuration = ConfigurationManager.get_configuration()

        self.assertEqual(configuration.stop_points, 30.0)
        self.assertEqual(configuration.target_points, 60.0)

    def test_run_experiment_sem_candles_retorna_estado_empty(self) -> None:
        """Garante experimento vazio sem falhar."""
        lab = ResearchLab()
        experiment = self._experiment(candles=[])

        completed = lab.run_experiment(experiment)

        self.assertEqual(completed.result.total_candles, 0)
        self.assertFalse(completed.result.is_finished)

    def test_run_strategy_benchmark_armazena_resultado(self) -> None:
        """Garante execucao e armazenamento de benchmark."""
        lab = ResearchLab()

        result = lab.run_strategy_benchmark(
            StaticStrategy(),
            self._benchmark_candles(),
        )

        self.assertIsInstance(result, StrategyBenchmarkResult)
        self.assertEqual(lab.list_benchmarks(), [result])

    def test_last_benchmark_retorna_ultimo_resultado(self) -> None:
        """Garante consulta do ultimo benchmark."""
        lab = ResearchLab()
        first = lab.run_strategy_benchmark(StaticStrategy(), [])
        second = lab.run_strategy_benchmark(
            StaticStrategy(),
            self._benchmark_candles(),
        )

        self.assertEqual(first.total_trades, 0)
        self.assertEqual(lab.last_benchmark(), second)

    def test_last_benchmark_retorna_none_sem_benchmarks(self) -> None:
        """Garante estado vazio do benchmark."""
        self.assertIsNone(ResearchLab().last_benchmark())

    def test_list_benchmarks_retorna_copia_da_lista(self) -> None:
        """Garante que lista interna de benchmarks nao vaza."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(StaticStrategy())

        benchmarks = lab.list_benchmarks()
        benchmarks.clear()

        self.assertEqual(len(lab.list_benchmarks()), 1)

    def test_clear_remove_benchmarks(self) -> None:
        """Garante limpeza dos benchmarks armazenados."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(StaticStrategy())

        lab.clear()

        self.assertEqual(lab.list_benchmarks(), [])
        self.assertIsNone(lab.last_benchmark())

    def test_compare_benchmarks_com_lista_vazia(self) -> None:
        """Garante comparacao vazia sem benchmarks."""
        comparison = ResearchLab().compare_benchmarks()

        self.assertIsInstance(comparison, BenchmarkComparison)
        self.assertIsNone(comparison.best_strategy)
        self.assertEqual(comparison.ranking, [])

    def test_compare_benchmarks_multiplos_resultados(self) -> None:
        """Garante comparacao de benchmarks armazenados."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(WaitStrategy(), self._benchmark_candles())
        lab.run_strategy_benchmark(StaticStrategy(), self._benchmark_candles())

        comparison = lab.compare_benchmarks()

        self.assertEqual(comparison.best_strategy, "lab_static_buy")
        self.assertEqual(len(comparison.ranking), 2)
        self.assertGreaterEqual(
            comparison.ranking[0].net_profit_points,
            comparison.ranking[1].net_profit_points,
        )

    def test_last_comparison_retorna_ultima_comparacao(self) -> None:
        """Garante armazenamento da ultima comparacao."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(StaticStrategy(), self._benchmark_candles())

        comparison = lab.compare_benchmarks()

        self.assertEqual(lab.last_comparison(), comparison)

    def test_clear_limpa_benchmarks_e_comparacao(self) -> None:
        """Garante limpeza de benchmarks e comparacao."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(StaticStrategy(), self._benchmark_candles())
        lab.compare_benchmarks()

        lab.clear()

        self.assertEqual(lab.list_benchmarks(), [])
        self.assertIsNone(lab.last_comparison())

    def test_parameter_grid_executa_todas_as_combinacoes(self) -> None:
        """Garante execucao de todas as combinacoes stop/target."""
        lab = ResearchLab()

        results = lab.run_parameter_grid(
            StaticStrategy(),
            stop_values=[30.0, 50.0],
            target_values=[60.0, 100.0],
        )

        self.assertEqual(len(results), 4)
        self.assertTrue(
            all(isinstance(item, ParameterGridResult) for item in results)
        )

    def test_parameter_grid_armazena_resultados(self) -> None:
        """Garante armazenamento dos resultados da grade."""
        lab = ResearchLab()

        results = lab.run_parameter_grid(
            StaticStrategy(),
            stop_values=[30.0],
            target_values=[60.0, 100.0],
        )

        self.assertEqual(lab.list_parameter_grid_results(), results)

    def test_parameter_grid_identifica_melhor_combinacao(self) -> None:
        """Garante identificacao da melhor combinacao por lucro."""
        lab = ResearchLab()
        results = lab.run_parameter_grid(
            StaticStrategy(),
            stop_values=[30.0],
            target_values=[60.0, 100.0],
        )

        best = lab.best_parameter_grid_result()

        expected = max(
            results,
            key=lambda result: result.benchmark.net_profit_points,
        )
        self.assertEqual(best, expected)

    def test_clear_limpa_parameter_grid(self) -> None:
        """Garante limpeza da grade de parametros."""
        lab = ResearchLab()
        lab.run_parameter_grid(
            StaticStrategy(),
            stop_values=[30.0],
            target_values=[60.0],
        )

        lab.clear()

        self.assertEqual(lab.list_parameter_grid_results(), [])
        self.assertIsNone(lab.best_parameter_grid_result())

    def test_validate_benchmark_armazena_validacao(self) -> None:
        """Garante validacao individual de benchmark."""
        lab = ResearchLab()
        benchmark = lab.run_strategy_benchmark(
            StaticStrategy(),
            self._benchmark_candles(),
        )

        validation = lab.validate_benchmark(benchmark)

        self.assertIsInstance(validation, ExperimentValidation)
        self.assertEqual(lab.list_validations(), [validation])

    def test_validate_all_benchmarks_valida_todos(self) -> None:
        """Garante validacao de todos os benchmarks armazenados."""
        lab = ResearchLab()
        lab.run_strategy_benchmark(WaitStrategy(), self._benchmark_candles())
        lab.run_strategy_benchmark(StaticStrategy(), self._benchmark_candles())

        validations = lab.validate_all_benchmarks()

        self.assertEqual(len(validations), 2)
        self.assertEqual(lab.list_validations(), validations)

    def test_last_validation_retorna_ultima_validacao(self) -> None:
        """Garante consulta da ultima validacao."""
        lab = ResearchLab()
        benchmark = lab.run_strategy_benchmark(
            StaticStrategy(),
            self._benchmark_candles(),
        )

        validation = lab.validate_benchmark(benchmark)

        self.assertEqual(lab.last_validation(), validation)

    def test_clear_limpa_validacoes(self) -> None:
        """Garante limpeza das validacoes."""
        lab = ResearchLab()
        benchmark = lab.run_strategy_benchmark(
            StaticStrategy(),
            self._benchmark_candles(),
        )
        lab.validate_benchmark(benchmark)

        lab.clear()

        self.assertEqual(lab.list_validations(), [])
        self.assertIsNone(lab.last_validation())

    def _experiment(
        self,
        experiment_name: str = "baseline",
        stop_points: float = 50.0,
        target_points: float = 100.0,
        candles: list[Candle] | None = None,
    ) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name=experiment_name,
            strategy_name="breakout",
            stop_points=stop_points,
            target_points=target_points,
            candles=self._candles() if candles is None else candles,
        )

    def _candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1002.0, 1000),
            Candle("2026-06-26 09:01", 1002.0, 1010.0, 999.0, 1008.0, 1000),
        ]

    def _benchmark_candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1000.0, 1000),
            Candle("2026-06-26 09:01", 1000.0, 1100.0, 999.0, 1100.0, 1000),
        ]


if __name__ == "__main__":
    unittest.main()
