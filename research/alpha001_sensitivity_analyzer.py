"""Analise de sensibilidade da Alpha001 por parametro."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_parameter_sweep import Alpha001ParameterSweepResult


@dataclass(frozen=True)
class Alpha001SensitivityResult:
    """Resultado da analise de impacto de um parametro Alpha001."""

    parameter_name: str
    best_value: object | None
    worst_value: object | None
    metric_impact: float
    sensitivity_level: str
    reasons: list[str]


@dataclass(frozen=True)
class Alpha001SensitivityAnalyzer:
    """Analisa sensibilidade usando apenas resultados ja existentes."""

    low_threshold: float = 25.0
    high_threshold: float = 100.0

    def analyze(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
        parameter_name: str,
    ) -> Alpha001SensitivityResult:
        """Calcula o impacto medio de um parametro no lucro liquido."""
        result_list = list(results)
        if parameter_name not in self._allowed_parameters():
            return self._empty_result(
                parameter_name,
                f"Parametro invalido: {parameter_name}.",
            )
        if not result_list:
            return self._empty_result(
                parameter_name,
                "Nenhum resultado disponivel para analise.",
            )
        groups = self._group_by_parameter(result_list, parameter_name)
        if len(groups) < 2:
            return self._single_value_result(parameter_name, groups)
        best_value, worst_value, impact = self._impact(groups)
        return Alpha001SensitivityResult(
            parameter_name=parameter_name,
            best_value=best_value,
            worst_value=worst_value,
            metric_impact=impact,
            sensitivity_level=self._sensitivity_level(impact),
            reasons=self._reasons(parameter_name, best_value, worst_value, impact),
        )

    def _allowed_parameters(self) -> set[str]:
        return {
            "opening_range_minutes",
            "minimum_range_size",
            "minimum_volume",
        }

    def _group_by_parameter(
        self,
        results: list[Alpha001ParameterSweepResult],
        parameter_name: str,
    ) -> dict[object, list[Alpha001ParameterSweepResult]]:
        groups: dict[object, list[Alpha001ParameterSweepResult]] = {}
        for result in results:
            value = getattr(result.parameters, parameter_name)
            groups.setdefault(value, []).append(result)
        return groups

    def _impact(
        self,
        groups: dict[object, list[Alpha001ParameterSweepResult]],
    ) -> tuple[object, object, float]:
        averages = {
            value: self._average_net_profit(items)
            for value, items in groups.items()
        }
        best_value = max(averages, key=averages.get)
        worst_value = min(averages, key=averages.get)
        return best_value, worst_value, averages[best_value] - averages[worst_value]

    def _average_net_profit(
        self,
        results: list[Alpha001ParameterSweepResult],
    ) -> float:
        return sum(result.net_profit_points for result in results) / len(results)

    def _sensitivity_level(self, impact: float) -> str:
        if impact <= self.low_threshold:
            return "LOW"
        if impact <= self.high_threshold:
            return "MEDIUM"
        return "HIGH"

    def _reasons(
        self,
        parameter_name: str,
        best_value: object,
        worst_value: object,
        impact: float,
    ) -> list[str]:
        return [
            f"Parametro analisado: {parameter_name}.",
            f"Melhor valor medio: {best_value}.",
            f"Pior valor medio: {worst_value}.",
            f"Impacto em pontos liquidos: {impact:.2f}.",
        ]

    def _empty_result(
        self,
        parameter_name: str,
        reason: str,
    ) -> Alpha001SensitivityResult:
        return Alpha001SensitivityResult(
            parameter_name=parameter_name,
            best_value=None,
            worst_value=None,
            metric_impact=0.0,
            sensitivity_level="LOW",
            reasons=[reason],
        )

    def _single_value_result(
        self,
        parameter_name: str,
        groups: dict[object, list[Alpha001ParameterSweepResult]],
    ) -> Alpha001SensitivityResult:
        value = next(iter(groups), None)
        return Alpha001SensitivityResult(
            parameter_name=parameter_name,
            best_value=value,
            worst_value=value,
            metric_impact=0.0,
            sensitivity_level="LOW",
            reasons=["Apenas um valor disponivel para o parametro."],
        )
