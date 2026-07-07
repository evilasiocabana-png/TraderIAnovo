"""Motor Walk-Forward estrutural da Alpha 001."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001WalkForwardMetrics:
    """Metricas estruturais de uma janela Walk-Forward."""

    total_experiments: int
    total_candles: int
    total_signals: int
    total_buy: int
    total_sell: int
    total_wait: int


@dataclass(frozen=True)
class Alpha001WalkForwardResult:
    """Resultado Walk-Forward da Alpha 001 por janelas fixas."""

    training_window: int
    validation_window: int
    testing_window: int
    training_metrics: Alpha001WalkForwardMetrics
    validation_metrics: Alpha001WalkForwardMetrics
    testing_metrics: Alpha001WalkForwardMetrics


@dataclass(frozen=True)
class Alpha001WalkForwardEngine:
    """Agrupa resultados existentes em janelas sem otimizar parametros."""

    training_window: int
    validation_window: int
    testing_window: int

    def calculate(
        self,
        results: Iterable[Alpha001ExperimentResult],
    ) -> Alpha001WalkForwardResult:
        """Calcula metricas estruturais por janela Walk-Forward."""
        result_list = list(results)
        training_results = result_list[: self.training_window]
        validation_start = self.training_window
        validation_end = validation_start + self.validation_window
        validation_results = result_list[validation_start:validation_end]
        testing_start = validation_end
        testing_end = testing_start + self.testing_window
        testing_results = result_list[testing_start:testing_end]

        return Alpha001WalkForwardResult(
            training_window=self.training_window,
            validation_window=self.validation_window,
            testing_window=self.testing_window,
            training_metrics=self._metrics(training_results),
            validation_metrics=self._metrics(validation_results),
            testing_metrics=self._metrics(testing_results),
        )

    def _metrics(
        self,
        results: list[Alpha001ExperimentResult],
    ) -> Alpha001WalkForwardMetrics:
        return Alpha001WalkForwardMetrics(
            total_experiments=len(results),
            total_candles=sum(result.total_candles for result in results),
            total_signals=sum(result.total_signals for result in results),
            total_buy=sum(result.total_buy for result in results),
            total_sell=sum(result.total_sell for result in results),
            total_wait=sum(result.total_wait for result in results),
        )
