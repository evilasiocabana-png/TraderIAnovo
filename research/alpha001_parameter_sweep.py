"""Varredura de parametros de pesquisa para a Alpha 001."""

from dataclasses import dataclass, field
from typing import Iterable

from domain.candle import Candle
from research.alpha001_experiment_validator import Alpha001ExperimentValidator
from research.alpha001_research_runner import Alpha001ResearchRunner
from research.research_lab import ResearchExperiment


@dataclass(frozen=True)
class Alpha001ParameterSet:
    """Parametros de uma combinacao de pesquisa Alpha 001."""

    opening_range_minutes: int
    minimum_range_size: float
    minimum_volume: int


@dataclass(frozen=True)
class Alpha001ParameterSweepResult:
    """Resultado de uma combinacao da varredura Alpha 001."""

    parameters: Alpha001ParameterSet
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float
    validation_status: str


@dataclass
class Alpha001ParameterSweep:
    """Executa pesquisa em lote variando parametros da Alpha 001."""

    runner: Alpha001ResearchRunner = field(default_factory=lambda: (
        Alpha001ResearchRunner(validator=_default_validator())
    ))

    def run(
        self,
        parameter_grid: Iterable[Alpha001ParameterSet | dict[str, object]],
    ) -> list[Alpha001ParameterSweepResult]:
        """Executa uma combinacao por vez preservando a ordem recebida."""
        results: list[Alpha001ParameterSweepResult] = []
        for index, raw_parameters in enumerate(parameter_grid):
            parameters = self._to_parameter_set(raw_parameters)
            experiment = self._to_experiment(index, parameters)
            research_result = self.runner.run([experiment])
            results.append(self._to_sweep_result(parameters, research_result))
        return results

    def _to_parameter_set(
        self,
        raw_parameters: Alpha001ParameterSet | dict[str, object],
    ) -> Alpha001ParameterSet:
        if isinstance(raw_parameters, Alpha001ParameterSet):
            return raw_parameters
        return Alpha001ParameterSet(
            opening_range_minutes=int(raw_parameters["opening_range_minutes"]),
            minimum_range_size=float(raw_parameters["minimum_range_size"]),
            minimum_volume=int(raw_parameters["minimum_volume"]),
        )

    def _to_experiment(
        self,
        index: int,
        parameters: Alpha001ParameterSet,
    ) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name=self._experiment_name(index, parameters),
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._candles(parameters),
        )

    def _to_sweep_result(
        self,
        parameters: Alpha001ParameterSet,
        research_result: object,
    ) -> Alpha001ParameterSweepResult:
        entry = research_result.validation_results[0]
        metrics = entry["metrics"]
        validation = entry["validation"]
        return Alpha001ParameterSweepResult(
            parameters=parameters,
            total_trades=int(metrics["total_trades"]),
            win_rate=float(metrics["win_rate"]),
            profit_factor=float(metrics["profit_factor"]),
            max_drawdown_points=float(metrics["max_drawdown_points"]),
            net_profit_points=float(metrics["net_profit_points"]),
            validation_status=str(validation.status),
        )

    def _experiment_name(
        self,
        index: int,
        parameters: Alpha001ParameterSet,
    ) -> str:
        return (
            f"alpha001_sweep_{index}_"
            f"or_{parameters.opening_range_minutes}_"
            f"range_{parameters.minimum_range_size}_"
            f"volume_{parameters.minimum_volume}"
        )

    def _candles(self, parameters: Alpha001ParameterSet) -> list[Candle]:
        breakout_minute = max(parameters.opening_range_minutes + 1, 16)
        volume = parameters.minimum_volume
        range_size = parameters.minimum_range_size
        opening_high = 100.0 + range_size
        breakout_close = opening_high + 6.0
        return [
            self._candle("09:00", 100.0, opening_high, 95.0, volume),
            self._candle("09:05", 105.0, 118.0, 98.0, volume),
            self._candle(
                f"09:{breakout_minute:02d}",
                breakout_close,
                breakout_close + 2.0,
                opening_high + 1.0,
                volume,
            ),
            self._candle(
                f"09:{breakout_minute + 1:02d}",
                breakout_close + 100.0,
                breakout_close + 104.0,
                breakout_close,
                volume,
            ),
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


def _default_validator() -> Alpha001ExperimentValidator:
    return Alpha001ExperimentValidator(
        minimum_total_trades=1,
        minimum_win_rate=0.0,
        minimum_profit_factor=0.0,
        maximum_drawdown_points=500.0,
        minimum_net_profit_points=-500.0,
    )
