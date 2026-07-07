"""Exportador em memoria dos resultados de pesquisa Alpha 001."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_parameter_sweep import Alpha001ParameterSweepResult


@dataclass(frozen=True)
class Alpha001ResultExporter:
    """Converte resultados Alpha001 para estruturas exportaveis."""

    def to_dict(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
    ) -> list[dict[str, object]]:
        """Converte resultados para lista de dicionarios."""
        return [self._result_to_dict(result) for result in results]

    def to_csv_rows(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
    ) -> list[list[object]]:
        """Converte resultados para linhas CSV em memoria."""
        rows = [self._csv_header()]
        rows.extend(
            [row[column] for column in self._csv_header()]
            for row in self.to_dict(results)
        )
        return rows

    def _result_to_dict(
        self,
        result: Alpha001ParameterSweepResult,
    ) -> dict[str, object]:
        return {
            "opening_range_minutes": result.parameters.opening_range_minutes,
            "minimum_range_size": result.parameters.minimum_range_size,
            "minimum_volume": result.parameters.minimum_volume,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "max_drawdown_points": result.max_drawdown_points,
            "net_profit_points": result.net_profit_points,
            "validation_status": result.validation_status,
            "recommendation": self._recommendation(result),
        }

    def _recommendation(
        self,
        result: Alpha001ParameterSweepResult,
    ) -> str:
        recommendations = {
            "APPROVED": "READY_FOR_EXTENDED_RESEARCH",
            "INSUFFICIENT_SAMPLE": "COLLECT_MORE_SAMPLES",
            "LOW_PROFIT_FACTOR": "REVIEW_ENTRY_FILTERS",
            "HIGH_DRAWDOWN": "REVIEW_RISK_PARAMETERS",
        }
        return recommendations.get(result.validation_status, "REVIEW_EXPERIMENT")

    def _csv_header(self) -> list[str]:
        return [
            "opening_range_minutes",
            "minimum_range_size",
            "minimum_volume",
            "total_trades",
            "win_rate",
            "profit_factor",
            "max_drawdown_points",
            "net_profit_points",
            "validation_status",
            "recommendation",
        ]
