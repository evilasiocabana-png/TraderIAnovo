"""Runner de pesquisa para experimentos completos da Alpha 001."""

from dataclasses import dataclass, field, replace
from typing import Iterable

from domain.contracts.backtest_result import BacktestResult
from research.alpha001_experiment_validator import (
    Alpha001ExperimentValidator,
    Alpha001ValidationResult,
)
from research.alpha001_research_advisor import (
    Alpha001ResearchAdvice,
    Alpha001ResearchAdvisor,
)
from research.research_lab import ResearchExperiment, ResearchLab


@dataclass(frozen=True)
class Alpha001ResearchResult:
    """Resultado consolidado da execucao de pesquisa da Alpha 001."""

    strategy_name: str
    total_experiments: int
    experiments_executed: int
    validation_results: list[dict[str, object]]
    summary: str
    approved: int = 0
    rejected: int = 0
    best_configuration: dict[str, object] | None = None
    statistical_summary: dict[str, float] = field(default_factory=dict)


@dataclass
class Alpha001ResearchRunner:
    """Orquestra ResearchLab, validator e advisor para a Alpha 001."""

    validator: Alpha001ExperimentValidator
    research_lab: ResearchLab = field(default_factory=ResearchLab)
    advisor: Alpha001ResearchAdvisor = field(default_factory=Alpha001ResearchAdvisor)
    strategy_name: str = "alpha001_iorb"

    def run(
        self,
        experiments: Iterable[ResearchExperiment],
    ) -> Alpha001ResearchResult:
        """Executa experimentos e consolida validacoes e recomendacoes."""
        experiment_list = list(experiments)
        validation_results = [
            self._run_single_experiment(experiment)
            for experiment in experiment_list
        ]
        return Alpha001ResearchResult(
            strategy_name=self.strategy_name,
            total_experiments=len(experiment_list),
            experiments_executed=len(validation_results),
            validation_results=validation_results,
            approved=self._approved_count(validation_results),
            rejected=self._rejected_count(validation_results),
            best_configuration=self._best_configuration(validation_results),
            statistical_summary=self._statistical_summary(validation_results),
            summary=self._summary(validation_results),
        )

    def _run_single_experiment(
        self,
        experiment: ResearchExperiment,
    ) -> dict[str, object]:
        alpha_experiment = replace(experiment, strategy_name=self.strategy_name)
        completed = self.research_lab.run_experiment(alpha_experiment)
        validation = self.validator.validate(self._to_backtest_result(completed))
        advice = self.advisor.analyze(validation)
        return self._validation_entry(completed, validation, advice)

    def _to_backtest_result(
        self,
        experiment: ResearchExperiment,
    ) -> BacktestResult:
        metrics = experiment.result.paper_metrics
        return BacktestResult(
            total_profit=metrics.net_profit_points,
            total_trades=metrics.total_trades,
            win_rate=metrics.win_rate,
            drawdown=metrics.max_drawdown_points,
            profit_factor=metrics.profit_factor,
            sharpe=0.0,
        )

    def _validation_entry(
        self,
        experiment: ResearchExperiment,
        validation: Alpha001ValidationResult,
        advice: Alpha001ResearchAdvice,
    ) -> dict[str, object]:
        metrics = validation.metrics
        return {
            "experiment_name": experiment.experiment_name,
            "configuration": self._configuration(experiment),
            "validation": validation,
            "advice": advice,
            "metrics": metrics,
            "approved": validation.approved,
            "net_profit_points": metrics["net_profit_points"],
        }

    def _summary(self, validation_results: list[dict[str, object]]) -> str:
        if not validation_results:
            return "Nenhum experimento Alpha 001 executado."
        approved = self._approved_count(validation_results)
        rejected = self._rejected_count(validation_results)
        best_configuration = self._best_configuration(validation_results)
        recommendations = [
            result["advice"].recommendation
            for result in validation_results
        ]
        best_name = "N/D"
        if best_configuration is not None:
            best_name = str(best_configuration["experiment_name"])
        return (
            f"{len(validation_results)} experimento(s) Alpha 001 executado(s). "
            f"Aprovados: {approved}. Rejeitados: {rejected}. "
            f"Melhor configuracao: {best_name}. "
            f"Recomendacoes: {', '.join(recommendations)}."
        )

    def _configuration(
        self,
        experiment: ResearchExperiment,
    ) -> dict[str, object]:
        return {
            "experiment_name": experiment.experiment_name,
            "strategy_name": experiment.strategy_name,
            "stop_points": experiment.stop_points,
            "target_points": experiment.target_points,
        }

    def _approved_count(
        self,
        validation_results: list[dict[str, object]],
    ) -> int:
        return sum(1 for result in validation_results if result["approved"])

    def _rejected_count(
        self,
        validation_results: list[dict[str, object]],
    ) -> int:
        return len(validation_results) - self._approved_count(validation_results)

    def _best_configuration(
        self,
        validation_results: list[dict[str, object]],
    ) -> dict[str, object] | None:
        if not validation_results:
            return None
        best = max(
            validation_results,
            key=lambda result: float(result["net_profit_points"]),
        )
        configuration = dict(best["configuration"])
        configuration["net_profit_points"] = best["net_profit_points"]
        configuration["experiment_name"] = best["experiment_name"]
        return configuration

    def _statistical_summary(
        self,
        validation_results: list[dict[str, object]],
    ) -> dict[str, float]:
        if not validation_results:
            return {
                "average_net_profit_points": 0.0,
                "average_win_rate": 0.0,
                "average_profit_factor": 0.0,
                "best_net_profit_points": 0.0,
            }
        metrics = [result["metrics"] for result in validation_results]
        return {
            "average_net_profit_points": self._average(
                [metric["net_profit_points"] for metric in metrics]
            ),
            "average_win_rate": self._average(
                [metric["win_rate"] for metric in metrics]
            ),
            "average_profit_factor": self._average(
                [metric["profit_factor"] for metric in metrics]
            ),
            "best_net_profit_points": max(
                float(metric["net_profit_points"]) for metric in metrics
            ),
        }

    def _average(self, values: list[float | int]) -> float:
        if not values:
            return 0.0
        return sum(float(value) for value in values) / len(values)
