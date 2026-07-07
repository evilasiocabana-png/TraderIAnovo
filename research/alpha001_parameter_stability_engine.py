"""Motor de estabilidade da Alpha 001 sob diferentes parametros."""

from dataclasses import dataclass
from typing import Iterable

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001ParameterStabilityResult:
    """Resultado da avaliacao de estabilidade parametrica."""

    variation_of_net_profit: float
    variation_of_drawdown: float
    variation_of_profit_factor: float
    variation_of_win_rate: float
    stable_strategy: bool


@dataclass(frozen=True)
class Alpha001ParameterStabilityEngine:
    """Avalia estabilidade usando apenas resultados ja existentes."""

    max_net_profit_variation: float = 100.0
    max_drawdown_variation: float = 50.0
    max_profit_factor_variation: float = 1.0
    max_win_rate_variation: float = 0.2

    def calculate(
        self,
        results: Iterable[Alpha001ResearchResult],
    ) -> Alpha001ParameterStabilityResult:
        """Calcula variacoes entre resultados de parametros existentes."""
        result_list = list(results)
        net_profit_variation = self._spread(
            [result.profit.net_profit_points for result in result_list],
        )
        drawdown_variation = self._spread(
            [result.drawdown.max_drawdown_points for result in result_list],
        )
        profit_factor_variation = self._spread(
            [result.profit_factor.profit_factor for result in result_list],
        )
        win_rate_variation = self._spread(
            [result.win_rate.win_rate for result in result_list],
        )
        return Alpha001ParameterStabilityResult(
            variation_of_net_profit=net_profit_variation,
            variation_of_drawdown=drawdown_variation,
            variation_of_profit_factor=profit_factor_variation,
            variation_of_win_rate=win_rate_variation,
            stable_strategy=self._stable(
                net_profit_variation,
                drawdown_variation,
                profit_factor_variation,
                win_rate_variation,
            ),
        )

    def _spread(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return float(max(values) - min(values))

    def _stable(
        self,
        net_profit_variation: float,
        drawdown_variation: float,
        profit_factor_variation: float,
        win_rate_variation: float,
    ) -> bool:
        return (
            net_profit_variation <= self.max_net_profit_variation
            and drawdown_variation <= self.max_drawdown_variation
            and profit_factor_variation <= self.max_profit_factor_variation
            and win_rate_variation <= self.max_win_rate_variation
        )
