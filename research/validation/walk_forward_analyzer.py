"""Analyzer de resultados Walk-Forward."""

from __future__ import annotations

from dataclasses import dataclass

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.walk_forward_engine import WalkForwardResult


@dataclass(frozen=True)
class WalkForwardAnalysisResult:
    """Resultado analitico de uma validacao Walk-Forward."""

    stability_score: float
    degradation_score: float
    consistency_score: float
    validation_score: float


@dataclass(frozen=True)
class WalkForwardAnalyzer:
    """Analisa janelas Walk-Forward sem recalcular metricas das Alphas."""

    def analyze(
        self,
        result: WalkForwardResult,
    ) -> WalkForwardAnalysisResult:
        """Calcula scores estruturais a partir do resultado Walk-Forward."""
        stability_score = self._completion_score(result.training_experiments)
        validation_window_score = self._completion_score(
            result.validation_experiments,
        )
        testing_score = self._completion_score(result.testing_experiments)
        consistency_score = self._consistency_score(
            stability_score,
            validation_window_score,
            testing_score,
        )
        degradation_score = self._degradation_score(
            stability_score,
            validation_window_score,
            testing_score,
        )
        validation_score = self._average(
            (
                stability_score,
                validation_window_score,
                testing_score,
                consistency_score,
                1.0 - degradation_score,
            )
        )
        return WalkForwardAnalysisResult(
            stability_score=stability_score,
            degradation_score=degradation_score,
            consistency_score=consistency_score,
            validation_score=validation_score,
        )

    def _completion_score(
        self,
        experiments: tuple[ExperimentDefinition, ...],
    ) -> float:
        if not experiments:
            return 0.0
        completed = sum(
            1
            for experiment in experiments
            if experiment.status.strip().upper() == "COMPLETED"
        )
        return self._clamp(completed / len(experiments))

    def _consistency_score(
        self,
        stability_score: float,
        validation_score: float,
        testing_score: float,
    ) -> float:
        scores = (stability_score, validation_score, testing_score)
        return self._clamp(1.0 - (max(scores) - min(scores)))

    def _degradation_score(
        self,
        stability_score: float,
        validation_score: float,
        testing_score: float,
    ) -> float:
        degradation = max(
            stability_score - validation_score,
            validation_score - testing_score,
            stability_score - testing_score,
            0.0,
        )
        return self._clamp(degradation)

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return self._clamp(sum(values) / len(values))

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
