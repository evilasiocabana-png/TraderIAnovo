"""Laboratorio quantitativo isolado para experimentos com replay."""

from dataclasses import asdict, dataclass, field, replace

from core.configuration_manager import ConfigurationManager
from alpha.alpha001_config import Alpha001Config
from domain.candle import Candle
from research.alpha001_experiment import (
    Alpha001Experiment,
    Alpha001ExperimentResult,
)
from research.benchmark_comparator import (
    BenchmarkComparator,
    BenchmarkComparison,
)
from research.experiment_validator import (
    ExperimentValidation,
    ExperimentValidator,
)
from research.strategy_benchmark import (
    StrategyBenchmark,
    StrategyBenchmarkResult,
)
from strategies.base import Strategy


@dataclass(frozen=True)
class ResearchExperiment:
    """Definicao e resultado de um experimento quantitativo."""

    experiment_name: str
    strategy_name: str
    stop_points: float
    target_points: float
    candles: list[Candle]
    result: object | None = None


@dataclass(frozen=True)
class ParameterGridResult:
    """Resultado de benchmark para uma combinacao stop/target."""

    stop_points: float
    target_points: float
    benchmark: StrategyBenchmarkResult


@dataclass
class ResearchLab:
    """Executa experimentos de replay sem broker, IA ou persistencia."""

    experiments: list[ResearchExperiment] = field(default_factory=list)
    benchmarks: list[StrategyBenchmarkResult] = field(default_factory=list)
    parameter_grid_results: list[ParameterGridResult] = field(
        default_factory=list
    )
    strategy_benchmark: StrategyBenchmark = field(
        default_factory=StrategyBenchmark
    )
    benchmark_comparator: BenchmarkComparator = field(
        default_factory=BenchmarkComparator
    )
    experiment_validator: ExperimentValidator = field(
        default_factory=ExperimentValidator
    )
    validations: list[ExperimentValidation] = field(default_factory=list)
    comparison: BenchmarkComparison | None = None

    def run_experiment(
        self,
        experiment: ResearchExperiment,
    ) -> ResearchExperiment:
        """Executa um replay e armazena o experimento finalizado."""
        original_configuration = ConfigurationManager.get_configuration()
        try:
            self._apply_experiment_configuration(experiment)
            result = self._run_single_replay(experiment.candles)
            completed = replace(experiment, result=result)
            self.experiments.append(completed)
            return completed
        finally:
            ConfigurationManager.update_configuration(
                **asdict(original_configuration)
            )

    def run_alpha001_experiment(
        self,
        experiment: ResearchExperiment,
        config: Alpha001Config | None = None,
    ) -> ResearchExperiment:
        """Executa Alpha001Experiment e armazena o experimento finalizado."""
        result = self._run_alpha001_experiment(experiment, config)
        completed = replace(experiment, result=result)
        self.experiments.append(completed)
        return completed

    def list_experiments(self) -> list[ResearchExperiment]:
        """Lista experimentos executados em memoria."""
        return list(self.experiments)

    def last_experiment(self) -> ResearchExperiment | None:
        """Retorna o ultimo experimento executado."""
        if not self.experiments:
            return None
        return self.experiments[-1]

    def clear(self) -> None:
        """Limpa os experimentos armazenados em memoria."""
        self.experiments.clear()
        self.benchmarks.clear()
        self.parameter_grid_results.clear()
        self.validations.clear()
        self.comparison = None

    def run_strategy_benchmark(
        self,
        strategy: Strategy,
        candles: list[Candle] | None = None,
    ) -> StrategyBenchmarkResult:
        """Executa benchmark de uma estrategia e armazena o resultado."""
        result = self.strategy_benchmark.run(
            strategy,
            self._benchmark_candles(candles),
        )
        self.benchmarks.append(result)
        return result

    def list_benchmarks(self) -> list[StrategyBenchmarkResult]:
        """Lista benchmarks executados em memoria."""
        return list(self.benchmarks)

    def last_benchmark(self) -> StrategyBenchmarkResult | None:
        """Retorna o ultimo benchmark executado."""
        if not self.benchmarks:
            return None
        return self.benchmarks[-1]

    def compare_benchmarks(self) -> BenchmarkComparison:
        """Compara todos os benchmarks armazenados em memoria."""
        self.comparison = self.benchmark_comparator.compare(
            self.benchmarks
        )
        return self.comparison

    def last_comparison(self) -> BenchmarkComparison | None:
        """Retorna a ultima comparacao realizada."""
        return self.comparison

    def run_parameter_grid(
        self,
        strategy: Strategy,
        stop_values: list[float],
        target_values: list[float],
    ) -> list[ParameterGridResult]:
        """Executa benchmarks para uma grade simples de parametros."""
        original_configuration = ConfigurationManager.get_configuration()
        results: list[ParameterGridResult] = []
        try:
            for stop_points in stop_values:
                for target_points in target_values:
                    result = self._run_grid_combination(
                        strategy,
                        stop_points,
                        target_points,
                    )
                    results.append(result)
                    self.parameter_grid_results.append(result)
            return results
        finally:
            ConfigurationManager.update_configuration(
                **asdict(original_configuration)
            )

    def list_parameter_grid_results(self) -> list[ParameterGridResult]:
        """Lista resultados da grade de parametros."""
        return list(self.parameter_grid_results)

    def best_parameter_grid_result(self) -> ParameterGridResult | None:
        """Retorna a melhor combinacao por lucro liquido."""
        if not self.parameter_grid_results:
            return None
        return max(
            self.parameter_grid_results,
            key=lambda result: result.benchmark.net_profit_points,
        )

    def validate_benchmark(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> ExperimentValidation:
        """Valida um benchmark e armazena o resultado."""
        validation = self.experiment_validator.validate(benchmark)
        self.validations.append(validation)
        return validation

    def validate_all_benchmarks(self) -> list[ExperimentValidation]:
        """Valida todos os benchmarks armazenados."""
        validations = [
            self.validate_benchmark(benchmark)
            for benchmark in self.benchmarks
        ]
        return validations

    def list_validations(self) -> list[ExperimentValidation]:
        """Lista validacoes estatisticas armazenadas."""
        return list(self.validations)

    def last_validation(self) -> ExperimentValidation | None:
        """Retorna a ultima validacao estatistica."""
        if not self.validations:
            return None
        return self.validations[-1]

    def _apply_experiment_configuration(
        self,
        experiment: ResearchExperiment,
    ) -> None:
        ConfigurationManager.update_configuration(
            stop_points=experiment.stop_points,
            target_points=experiment.target_points,
        )

    def _run_grid_combination(
        self,
        strategy: Strategy,
        stop_points: float,
        target_points: float,
    ) -> ParameterGridResult:
        ConfigurationManager.update_configuration(
            stop_points=stop_points,
            target_points=target_points,
        )
        benchmark = self.strategy_benchmark.run(
            strategy,
            self._default_benchmark_candles(),
        )
        return ParameterGridResult(
            stop_points=stop_points,
            target_points=target_points,
            benchmark=benchmark,
        )

    def _run_single_replay(self, candles: list[Candle]) -> object:
        from application.replay_service import ReplayService

        replay_service = ReplayService()
        replay_service.replay_engine.load_candles(list(candles))
        replay_service.status = self._initial_status(candles)
        data = replay_service.get_replay_data()
        while not data.is_finished and candles:
            data = replay_service.next_candle()
        return data

    def _initial_status(self, candles: list[Candle]) -> object:
        from application.replay_service import ReplayStatus

        if candles:
            return ReplayStatus.READY
        return ReplayStatus.EMPTY

    def _run_alpha001_experiment(
        self,
        experiment: ResearchExperiment,
        config: Alpha001Config | None,
    ) -> Alpha001ExperimentResult:
        alpha_config = config or Alpha001Config(
            initial_stop_points=experiment.stop_points,
            initial_target_points=experiment.target_points,
        )
        return Alpha001Experiment(
            config=alpha_config,
            candles=experiment.candles,
        ).run()

    def _benchmark_candles(
        self,
        candles: list[Candle] | None,
    ) -> list[Candle]:
        if candles is None:
            return self._default_benchmark_candles()
        return list(candles)

    def _default_benchmark_candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1000.0, 1000),
            Candle("2026-06-26 09:01", 1000.0, 1100.0, 999.0, 1100.0, 1000),
        ]
