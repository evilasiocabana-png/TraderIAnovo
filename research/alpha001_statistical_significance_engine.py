"""Motor de significancia estatistica da Alpha 001."""

from dataclasses import dataclass
from math import sqrt

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001StatisticalSignificanceResult:
    """Indicadores estatisticos da Alpha 001."""

    mean_return: float
    standard_deviation: float
    standard_error: float
    t_score: float
    significance_flag: bool


@dataclass(frozen=True)
class Alpha001StatisticalSignificanceEngine:
    """Produz indicadores estatisticos sem executar novas simulacoes."""

    significance_threshold: float = 2.0

    def calculate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001StatisticalSignificanceResult:
        """Calcula indicadores a partir de resultados ja consolidados."""
        returns = self._trade_returns(research_result)
        if not returns:
            return Alpha001StatisticalSignificanceResult(
                mean_return=0.0,
                standard_deviation=0.0,
                standard_error=0.0,
                t_score=0.0,
                significance_flag=False,
            )

        mean_return = self._mean(returns)
        standard_deviation = self._sample_standard_deviation(
            returns,
            mean_return,
        )
        standard_error = self._standard_error(
            standard_deviation,
            len(returns),
        )
        t_score = self._t_score(mean_return, standard_error)
        return Alpha001StatisticalSignificanceResult(
            mean_return=mean_return,
            standard_deviation=standard_deviation,
            standard_error=standard_error,
            t_score=t_score,
            significance_flag=abs(t_score) >= self.significance_threshold,
        )

    def _trade_returns(
        self,
        research_result: Alpha001ResearchResult,
    ) -> list[float]:
        wins = [
            max(float(research_result.expectancy.average_win), 0.0)
            for _ in range(research_result.win_rate.winning_trades)
        ]
        losses = [
            -abs(float(research_result.expectancy.average_loss))
            for _ in range(research_result.win_rate.losing_trades)
        ]
        breakevens = [
            0.0
            for _ in range(research_result.win_rate.breakeven_trades)
        ]
        return [*wins, *losses, *breakevens]

    def _mean(self, values: list[float]) -> float:
        return float(sum(values) / len(values))

    def _sample_standard_deviation(
        self,
        values: list[float],
        mean: float,
    ) -> float:
        if len(values) < 2:
            return 0.0
        variance = sum((value - mean) ** 2 for value in values) / (
            len(values) - 1
        )
        return float(sqrt(variance))

    def _standard_error(
        self,
        standard_deviation: float,
        sample_size: int,
    ) -> float:
        if sample_size <= 0:
            return 0.0
        return float(standard_deviation / sqrt(sample_size))

    def _t_score(self, mean_return: float, standard_error: float) -> float:
        if standard_error == 0.0:
            return 0.0
        return float(mean_return / standard_error)
