"""Motor de dependencia de operacoes extremas da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001OutlierResult:
    """Resultado da avaliacao de operacoes extremas."""

    largest_winning_trade: float
    largest_losing_trade: float
    largest_trade_contribution_percent: float
    outlier_detected: bool


@dataclass(frozen=True)
class Alpha001OutlierEngine:
    """Identifica dependencia excessiva de extremos sem alterar resultados."""

    contribution_threshold_percent: float = 50.0

    def calculate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001OutlierResult:
        """Calcula participacao estimada da maior operacao agregada."""
        largest_winner = self._largest_winner(research_result)
        largest_loser = self._largest_loser(research_result)
        largest_trade = max(largest_winner, largest_loser)
        contribution = self._contribution_percent(
            largest_trade,
            research_result,
        )
        return Alpha001OutlierResult(
            largest_winning_trade=largest_winner,
            largest_losing_trade=largest_loser,
            largest_trade_contribution_percent=contribution,
            outlier_detected=contribution >= self.contribution_threshold_percent,
        )

    def _largest_winner(self, research_result: Alpha001ResearchResult) -> float:
        if research_result.win_rate.winning_trades <= 0:
            return 0.0
        return max(float(research_result.expectancy.average_win), 0.0)

    def _largest_loser(self, research_result: Alpha001ResearchResult) -> float:
        if research_result.win_rate.losing_trades <= 0:
            return 0.0
        return abs(float(research_result.expectancy.average_loss))

    def _contribution_percent(
        self,
        largest_trade: float,
        research_result: Alpha001ResearchResult,
    ) -> float:
        total_movement = (
            abs(float(research_result.profit.gross_profit_points))
            + abs(float(research_result.profit.gross_loss_points))
        )
        if total_movement == 0:
            return 0.0
        return (largest_trade / total_movement) * 100.0
