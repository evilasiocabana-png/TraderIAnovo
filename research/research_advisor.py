"""Recomendador estatistico isolado para resultados do Research Lab."""

from dataclasses import dataclass, field

from research.benchmark_comparator import BenchmarkComparison
from research.experiment_validator import ExperimentValidation
from research.strategy_benchmark import StrategyBenchmarkResult


@dataclass(frozen=True)
class ResearchRecommendation:
    """Recomendacao baseada em benchmark e validacao estatistica."""

    recommended_strategy: str | None
    reason: str
    confidence: float
    benchmark_used: StrategyBenchmarkResult | None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResearchAdvisor:
    """Recomenda estrategias sem IA, ordens ou execucao operacional."""

    def recommend(
        self,
        benchmark_comparison: BenchmarkComparison,
        experiment_validation: ExperimentValidation,
    ) -> ResearchRecommendation:
        """Gera recomendacao a partir de benchmark e validacao."""
        benchmark = self._best_benchmark(benchmark_comparison)
        warnings = list(experiment_validation.warnings)
        if benchmark is None:
            return self._no_benchmark_recommendation(warnings)
        if not experiment_validation.is_statistically_relevant:
            return self._not_relevant_recommendation(
                benchmark,
                experiment_validation,
                warnings,
            )
        if not self._has_clear_winner(benchmark_comparison):
            return self._no_clear_winner_recommendation(benchmark, warnings)
        return self._positive_recommendation(
            benchmark,
            experiment_validation,
            warnings,
        )

    def _best_benchmark(
        self,
        comparison: BenchmarkComparison,
    ) -> StrategyBenchmarkResult | None:
        if not comparison.ranking:
            return None
        return comparison.ranking[0]

    def _has_clear_winner(self, comparison: BenchmarkComparison) -> bool:
        if len(comparison.ranking) == 1:
            return True
        best = comparison.ranking[0]
        second = comparison.ranking[1]
        return best.net_profit_points > second.net_profit_points

    def _no_benchmark_recommendation(
        self,
        warnings: list[str],
    ) -> ResearchRecommendation:
        return ResearchRecommendation(
            recommended_strategy=None,
            reason="Nenhum benchmark disponivel para recomendacao.",
            confidence=0.0,
            benchmark_used=None,
            warnings=warnings + ["Nenhum benchmark disponivel"],
        )

    def _not_relevant_recommendation(
        self,
        benchmark: StrategyBenchmarkResult,
        validation: ExperimentValidation,
        warnings: list[str],
    ) -> ResearchRecommendation:
        return ResearchRecommendation(
            recommended_strategy=None,
            reason=(
                "Nao ha recomendacao porque a amostra ainda nao e "
                f"estatisticamente relevante ({validation.confidence_level})."
            ),
            confidence=0.0,
            benchmark_used=benchmark,
            warnings=warnings + ["Amostra estatisticamente insuficiente"],
        )

    def _no_clear_winner_recommendation(
        self,
        benchmark: StrategyBenchmarkResult,
        warnings: list[str],
    ) -> ResearchRecommendation:
        return ResearchRecommendation(
            recommended_strategy=None,
            reason=(
                "Nao ha recomendacao porque nenhuma estrategia ficou "
                "claramente superior no benchmark."
            ),
            confidence=40.0,
            benchmark_used=benchmark,
            warnings=warnings + ["Sem estrategia claramente superior"],
        )

    def _positive_recommendation(
        self,
        benchmark: StrategyBenchmarkResult,
        validation: ExperimentValidation,
        warnings: list[str],
    ) -> ResearchRecommendation:
        return ResearchRecommendation(
            recommended_strategy=benchmark.strategy_name,
            reason=(
                f"A estrategia {benchmark.strategy_name} foi recomendada "
                "por liderar o ranking com melhor lucro liquido."
            ),
            confidence=self._confidence(validation, warnings),
            benchmark_used=benchmark,
            warnings=warnings,
        )

    def _confidence(
        self,
        validation: ExperimentValidation,
        warnings: list[str],
    ) -> float:
        base = self._base_confidence(validation.confidence_level)
        return max(base - len(warnings) * 5.0, 0.0)

    def _base_confidence(self, confidence_level: str) -> float:
        if confidence_level == "Confiabilidade alta":
            return 85.0
        if confidence_level == "Confiabilidade media":
            return 65.0
        return 0.0
