"""Analise de estabilidade temporal da Alpha001."""

from dataclasses import dataclass
from typing import Iterable

from research.period_performance_analyzer import PeriodPerformanceReport


@dataclass(frozen=True)
class TemporalStabilityResult:
    """Resultado da analise de estabilidade temporal."""

    stability_score: float
    status: str
    reasons: list[str]


@dataclass(frozen=True)
class TemporalStabilityAnalyzer:
    """Avalia estabilidade usando resultados por periodo existentes."""

    profit_factor_spread_limit: float = 0.75
    drawdown_spread_limit: float = 50.0
    positive_ratio_limit: float = 0.60
    recent_degradation_limit: float = 0.25

    def analyze(
        self,
        period_results: Iterable[PeriodPerformanceReport],
    ) -> TemporalStabilityResult:
        """Calcula estabilidade temporal sem executar novos experimentos."""
        results = sorted(list(period_results), key=lambda item: item.period)
        if len(results) < 2:
            return TemporalStabilityResult(
                stability_score=0.0,
                status="INCONCLUSIVE",
                reasons=["Amostra temporal insuficiente."],
            )
        reasons = self._reasons(results)
        score = self._score(reasons)
        return TemporalStabilityResult(
            stability_score=score,
            status=self._status(score),
            reasons=reasons,
        )

    def _reasons(
        self,
        results: list[PeriodPerformanceReport],
    ) -> list[str]:
        return [
            self._profit_factor_reason(results),
            self._drawdown_reason(results),
            self._positive_negative_reason(results),
            self._recent_degradation_reason(results),
        ]

    def _score(self, reasons: list[str]) -> float:
        points = 0
        points += 25 if "Profit factor consistente." in reasons else 0
        points += 25 if "Drawdown estavel." in reasons else 0
        points += 25 if "Maioria dos periodos positiva." in reasons else 0
        points += 25 if "Sem degradacao recente relevante." in reasons else 0
        return float(points)

    def _status(self, score: float) -> str:
        if score >= 100.0:
            return "STABLE"
        return "UNSTABLE"

    def _profit_factor_reason(
        self,
        results: list[PeriodPerformanceReport],
    ) -> str:
        values = [result.metrics.profit_factor for result in results]
        if self._spread(values) <= self.profit_factor_spread_limit:
            return "Profit factor consistente."
        return "Profit factor instavel."

    def _drawdown_reason(
        self,
        results: list[PeriodPerformanceReport],
    ) -> str:
        values = [result.metrics.max_drawdown_points for result in results]
        if self._spread(values) <= self.drawdown_spread_limit:
            return "Drawdown estavel."
        return "Drawdown variavel."

    def _positive_negative_reason(
        self,
        results: list[PeriodPerformanceReport],
    ) -> str:
        positives = [
            result
            for result in results
            if result.metrics.net_profit_points > 0
        ]
        if len(positives) / len(results) >= self.positive_ratio_limit:
            return "Maioria dos periodos positiva."
        return "Periodos negativos excessivos."

    def _recent_degradation_reason(
        self,
        results: list[PeriodPerformanceReport],
    ) -> str:
        midpoint = max(len(results) // 2, 1)
        previous = results[:midpoint]
        recent = results[midpoint:]
        previous_average = self._average_profit(previous)
        recent_average = self._average_profit(recent)
        if previous_average <= 0:
            return "Sem degradacao recente relevante."
        degradation = (previous_average - recent_average) / previous_average
        if degradation <= self.recent_degradation_limit:
            return "Sem degradacao recente relevante."
        return "Degradacao recente de performance."

    def _average_profit(self, results: list[PeriodPerformanceReport]) -> float:
        if not results:
            return 0.0
        return sum(result.metrics.net_profit_points for result in results) / len(results)

    def _spread(self, values: list[float]) -> float:
        return max(values) - min(values)
