"""Walk-forward runner da Alpha001 sobre treino e teste."""

from dataclasses import dataclass, field

from domain.candle import Candle
from research.alpha001_experiment_validator import Alpha001ExperimentValidator
from research.alpha001_research_runner import (
    Alpha001ResearchRunner,
)
from research.research_lab import ResearchExperiment


@dataclass(frozen=True)
class WalkForwardResult:
    """Resultado consolidado do walk-forward Alpha001."""

    train_result: dict[str, object]
    test_result: dict[str, object]
    overfitting_score: float
    robustness_status: str


@dataclass
class WalkForwardRunner:
    """Executa Alpha001 em treino e teste sem recalibrar parametros."""

    runner: Alpha001ResearchRunner = field(
        default_factory=lambda: Alpha001ResearchRunner(
            validator=_default_validator(),
        )
    )
    stop_points: float = 50.0
    target_points: float = 100.0

    def run(
        self,
        train_dataset: list[Candle],
        test_dataset: list[Candle],
    ) -> WalkForwardResult:
        """Executa treino e teste com a mesma configuracao."""
        train_result = self._run_dataset("walk_forward_train", train_dataset)
        test_result = self._run_dataset("walk_forward_test", test_dataset)
        score = self._overfitting_score(train_result, test_result)
        return WalkForwardResult(
            train_result=train_result,
            test_result=test_result,
            overfitting_score=score,
            robustness_status=self._robustness_status(score),
        )

    def _run_dataset(
        self,
        experiment_name: str,
        candles: list[Candle],
    ) -> dict[str, object]:
        result = self.runner.run(
            [
                ResearchExperiment(
                    experiment_name=experiment_name,
                    strategy_name="alpha001_iorb",
                    stop_points=self.stop_points,
                    target_points=self.target_points,
                    candles=list(candles),
                )
            ]
        )
        return dict(result.validation_results[0])

    def _overfitting_score(
        self,
        train_result: dict[str, object],
        test_result: dict[str, object],
    ) -> float:
        train_profit = self._net_profit(train_result)
        test_profit = self._net_profit(test_result)
        if train_profit <= 0:
            return 0.0 if test_profit >= train_profit else 100.0
        degradation = max(train_profit - test_profit, 0.0)
        return min((degradation / abs(train_profit)) * 100.0, 100.0)

    def _net_profit(self, result: dict[str, object]) -> float:
        metrics = result["metrics"]
        return float(metrics["net_profit_points"])

    def _robustness_status(self, overfitting_score: float) -> str:
        if overfitting_score <= 25.0:
            return "ROBUST"
        if overfitting_score <= 60.0:
            return "DEGRADED"
        return "OVERFITTED"


def _default_validator() -> Alpha001ExperimentValidator:
    return Alpha001ExperimentValidator(
        minimum_total_trades=1,
        minimum_win_rate=0.0,
        minimum_profit_factor=0.0,
        maximum_drawdown_points=500.0,
        minimum_net_profit_points=-500.0,
    )
