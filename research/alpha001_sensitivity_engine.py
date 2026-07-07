"""Motor de sensibilidade da Alpha 001 sobre resultados ja calculados."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001SensitivityResult:
    """Resultado da analise de sensibilidade parametrica."""

    variation_of_net_profit: float
    variation_of_drawdown: float
    variation_of_profit_factor: float
    variation_of_win_rate: float


@dataclass(frozen=True)
class Alpha001SensitivityEngine:
    """Mede variacoes entre resultados sem otimizar parametros."""

    def calculate(
        self,
        results: Iterable[Alpha001ResearchResult],
    ) -> Alpha001SensitivityResult:
        """Calcula variacoes entre metricas de resultados existentes."""
        result_list = list(results)
        return Alpha001SensitivityResult(
            variation_of_net_profit=self._spread(
                [result.profit.net_profit_points for result in result_list],
            ),
            variation_of_drawdown=self._spread(
                [result.drawdown.max_drawdown_points for result in result_list],
            ),
            variation_of_profit_factor=self._spread(
                [result.profit_factor.profit_factor for result in result_list],
            ),
            variation_of_win_rate=self._spread(
                [result.win_rate.win_rate for result in result_list],
            ),
        )

    def _spread(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return float(max(values) - min(values))
