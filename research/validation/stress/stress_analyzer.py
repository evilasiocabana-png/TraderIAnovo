"""Analyzer oficial dos resultados sob estresse."""

from __future__ import annotations

from dataclasses import dataclass

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.stress.stress_engine import StressResult


@dataclass(frozen=True)
class StressAnalysisResult:
    """Resultado analitico da validacao por estresse."""

    degradation_score: float
    recovery_score: float
    resilience_score: float
    stability_score: float


@dataclass(frozen=True)
class StressAnalyzer:
    """Analisa resultados sob estresse sem recalcular metricas das Alphas."""

    def analyze(
        self,
        result: StressResult,
    ) -> StressAnalysisResult:
        """Calcula scores estruturais a partir do resultado sob estresse."""
        if not result.scenario_enabled:
            return StressAnalysisResult(
                degradation_score=0.0,
                recovery_score=0.0,
                resilience_score=0.0,
                stability_score=0.0,
            )
        stability_score = self._completion_score(result.executed_experiments)
        degradation_score = self._degradation_score(
            result.scenario.severity,
            stability_score,
        )
        recovery_score = self._recovery_score(result.status, stability_score)
        resilience_score = self._average(
            (
                stability_score,
                recovery_score,
                1.0 - degradation_score,
            )
        )
        return StressAnalysisResult(
            degradation_score=degradation_score,
            recovery_score=recovery_score,
            resilience_score=resilience_score,
            stability_score=stability_score,
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

    def _degradation_score(
        self,
        severity: float,
        stability_score: float,
    ) -> float:
        severity_penalty = self._clamp(severity)
        stability_penalty = 1.0 - self._clamp(stability_score)
        return self._average((severity_penalty, stability_penalty))

    def _recovery_score(
        self,
        status: str,
        stability_score: float,
    ) -> float:
        if status.strip().upper() != "COMPLETED":
            return 0.0
        return self._clamp(stability_score)

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return self._clamp(sum(values) / len(values))

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
