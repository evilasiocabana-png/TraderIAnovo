"""Ranking de resultados da varredura de parametros Alpha 001."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_parameter_sweep import Alpha001ParameterSweepResult


@dataclass(frozen=True)
class Alpha001ParameterRanking:
    """Ordena resultados existentes sem executar novas pesquisas."""

    def rank(
        self,
        results: Iterable[Alpha001ParameterSweepResult],
    ) -> list[Alpha001ParameterSweepResult]:
        """Retorna resultados ordenados pelos criterios oficiais."""
        return sorted(
            list(results),
            key=self._ranking_key,
        )

    def _ranking_key(
        self,
        result: Alpha001ParameterSweepResult,
    ) -> tuple[bool, float, float, float, int]:
        return (
            result.validation_status != "APPROVED",
            -result.profit_factor,
            result.max_drawdown_points,
            -result.net_profit_points,
            -result.total_trades,
        )
