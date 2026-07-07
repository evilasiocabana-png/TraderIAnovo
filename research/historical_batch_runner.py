"""Execucao em lote da Alpha001 sobre datasets historicos carregados."""

from dataclasses import dataclass, field
from typing import Iterable

from domain.candle import Candle
from research.alpha001_experiment_validator import Alpha001ExperimentValidator
from research.alpha001_research_runner import (
    Alpha001ResearchResult,
    Alpha001ResearchRunner,
)
from research.research_lab import ResearchExperiment


@dataclass(frozen=True)
class HistoricalDataset:
    """Dataset historico ja carregado para pesquisa."""

    name: str
    candles: list[Candle]


@dataclass(frozen=True)
class HistoricalBatchResult:
    """Resultado consolidado do lote historico Alpha001."""

    total_datasets: int
    datasets_executed: int
    results: list[dict[str, object]]
    summary: str
    approved: int = 0
    rejected: int = 0
    best_dataset: str | None = None
    statistical_summary: dict[str, float] = field(default_factory=dict)


@dataclass
class HistoricalBatchRunner:
    """Orquestra Alpha001 em multiplos datasets historicos."""

    runner: Alpha001ResearchRunner = field(
        default_factory=lambda: Alpha001ResearchRunner(
            validator=_default_validator(),
        )
    )

    def run(
        self,
        datasets: Iterable[HistoricalDataset | dict[str, object] | list[Candle]],
    ) -> HistoricalBatchResult:
        """Executa Alpha001 em cada dataset ja carregado."""
        dataset_list = [
            self._to_dataset(dataset, index)
            for index, dataset in enumerate(datasets, start=1)
        ]
        research_result = self.runner.run(
            self._experiments(dataset_list),
        )
        return self._to_batch_result(dataset_list, research_result)

    def _to_dataset(
        self,
        dataset: HistoricalDataset | dict[str, object] | list[Candle],
        index: int,
    ) -> HistoricalDataset:
        if isinstance(dataset, HistoricalDataset):
            return dataset
        if isinstance(dataset, dict):
            return HistoricalDataset(
                name=str(dataset.get("name", f"dataset_{index}")),
                candles=list(dataset.get("candles", [])),
            )
        return HistoricalDataset(name=f"dataset_{index}", candles=list(dataset))

    def _experiments(
        self,
        datasets: list[HistoricalDataset],
    ) -> list[ResearchExperiment]:
        return [
            ResearchExperiment(
                experiment_name=dataset.name,
                strategy_name="alpha001_iorb",
                stop_points=50.0,
                target_points=100.0,
                candles=list(dataset.candles),
            )
            for dataset in datasets
        ]

    def _to_batch_result(
        self,
        datasets: list[HistoricalDataset],
        research_result: Alpha001ResearchResult,
    ) -> HistoricalBatchResult:
        best = research_result.best_configuration
        return HistoricalBatchResult(
            total_datasets=len(datasets),
            datasets_executed=research_result.experiments_executed,
            results=list(research_result.validation_results),
            summary=self._summary(research_result),
            approved=research_result.approved,
            rejected=research_result.rejected,
            best_dataset=self._best_dataset_name(best),
            statistical_summary=dict(research_result.statistical_summary),
        )

    def _summary(self, result: Alpha001ResearchResult) -> str:
        return (
            f"{result.experiments_executed} dataset(s) historico(s) "
            f"executado(s) com Alpha001. "
            f"Aprovados: {result.approved}. Rejeitados: {result.rejected}."
        )

    def _best_dataset_name(self, best: dict[str, object] | None) -> str | None:
        if best is None:
            return None
        return str(best["experiment_name"])


def _default_validator() -> Alpha001ExperimentValidator:
    return Alpha001ExperimentValidator(
        minimum_total_trades=1,
        minimum_win_rate=0.0,
        minimum_profit_factor=0.0,
        maximum_drawdown_points=500.0,
        minimum_net_profit_points=-500.0,
    )
