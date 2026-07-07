"""Analise de robustez da Alpha001 por configuracao."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_parameter_sweep import Alpha001ParameterSweepResult


@dataclass(frozen=True)
class Alpha001RobustnessResult:
    """Resultado da analise de robustez Alpha001."""

    robustness_score: float
    status: str
    reasons: list[str]


@dataclass(frozen=True)
class Alpha001RobustnessAnalyzer:
    """Avalia robustez usando apenas resultados ja existentes."""

    minimum_trades: int = 30

    def analyze(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
    ) -> Alpha001RobustnessResult:
        """Analisa consistencia, drawdown, amostra e estabilidade."""
        result_list = list(results)
        if not result_list:
            return Alpha001RobustnessResult(
                robustness_score=0.0,
                status="INCONCLUSIVE",
                reasons=["Nenhum resultado disponivel para analise."],
            )
        reasons = self._reasons(result_list)
        score = self._score(result_list, reasons)
        return Alpha001RobustnessResult(
            robustness_score=score,
            status=self._status(score, reasons),
            reasons=reasons,
        )

    def _reasons(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> list[str]:
        reasons: list[str] = []
        reasons.append(self._profit_factor_reason(results))
        reasons.append(self._drawdown_reason(results))
        reasons.append(self._trades_reason(results))
        reasons.append(self._stability_reason(results))
        return reasons

    def _score(
        self,
        results: list[Alpha001ParameterSweepResult],
        reasons: list[str],
    ) -> float:
        points = 0
        points += 25 if "Profit factor consistente." in reasons else 0
        points += 25 if "Drawdown relativo controlado." in reasons else 0
        points += 25 if "Quantidade minima de trades atendida." in reasons else 0
        points += 25 if "Configuracoes proximas estaveis." in reasons else 0
        if any(result.validation_status == "APPROVED" for result in results):
            return float(points)
        return min(float(points), 50.0)

    def _status(self, score: float, reasons: list[str]) -> str:
        if "Quantidade minima de trades insuficiente." in reasons:
            return "INCONCLUSIVE"
        if score >= 100.0:
            return "ROBUST"
        return "FRAGILE"

    def _profit_factor_reason(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> str:
        profit_factors = [result.profit_factor for result in results]
        if min(profit_factors) >= 1.0 and self._spread(profit_factors) <= 1.0:
            return "Profit factor consistente."
        return "Profit factor inconsistente."

    def _drawdown_reason(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> str:
        ratios = [self._drawdown_ratio(result) for result in results]
        if max(ratios) <= 0.5:
            return "Drawdown relativo controlado."
        return "Drawdown relativo elevado."

    def _trades_reason(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> str:
        if min(result.total_trades for result in results) >= self.minimum_trades:
            return "Quantidade minima de trades atendida."
        return "Quantidade minima de trades insuficiente."

    def _stability_reason(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> str:
        ordered = sorted(
            results,
            key=lambda result: result.parameters.opening_range_minutes,
        )
        profits = [result.net_profit_points for result in ordered]
        if len(profits) < 2 or self._spread(profits) <= 100.0:
            return "Configuracoes proximas estaveis."
        return "Configuracoes proximas instaveis."

    def _drawdown_ratio(self, result: Alpha001ParameterSweepResult) -> float:
        profit = abs(result.net_profit_points)
        if profit == 0:
            return 0.0 if result.max_drawdown_points == 0 else 1.0
        return result.max_drawdown_points / profit

    def _spread(self, values: list[float]) -> float:
        return max(values) - min(values)
