"""Validador de qualidade estatistica da pesquisa Alpha 001."""

from dataclasses import dataclass, field

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001ResearchValidationResult:
    """Resultado da validacao estatistica de pesquisa Alpha 001."""

    approved: bool
    status: str
    reasons: tuple[str, ...]
    minimum_trades: int
    minimum_profit_factor: float
    maximum_drawdown: float
    minimum_win_rate: float
    real_trading_authorized: bool = False


@dataclass(frozen=True)
class Alpha001ResearchValidator:
    """Valida Alpha001ResearchResult sem recalcular metricas."""

    minimum_trades: int
    minimum_profit_factor: float
    maximum_drawdown: float
    minimum_win_rate: float
    approved_reason: str = "Pesquisa Alpha001 atende aos criterios estatisticos."
    _insufficient_trades_reason: str = field(
        default="Quantidade de trades abaixo do minimo configurado.",
        init=False,
        repr=False,
    )
    _low_profit_factor_reason: str = field(
        default="Profit factor abaixo do minimo configurado.",
        init=False,
        repr=False,
    )
    _high_drawdown_reason: str = field(
        default="Drawdown acima do maximo configurado.",
        init=False,
        repr=False,
    )
    _low_win_rate_reason: str = field(
        default="Win rate abaixo do minimo configurado.",
        init=False,
        repr=False,
    )

    def validate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001ResearchValidationResult:
        """Valida qualidade estatistica sem autorizar operacao real."""
        reasons = tuple(self._rejection_reasons(research_result))
        status = self._status(reasons)
        return Alpha001ResearchValidationResult(
            approved=status == "APPROVED",
            status=status,
            reasons=reasons or (self.approved_reason,),
            minimum_trades=self.minimum_trades,
            minimum_profit_factor=self.minimum_profit_factor,
            maximum_drawdown=self.maximum_drawdown,
            minimum_win_rate=self.minimum_win_rate,
            real_trading_authorized=False,
        )

    def _rejection_reasons(
        self,
        research_result: Alpha001ResearchResult,
    ) -> list[str]:
        reasons: list[str] = []
        if research_result.metrics.total_trades < self.minimum_trades:
            reasons.append(self._insufficient_trades_reason)
        if (
            research_result.profit_factor.profit_factor
            < self.minimum_profit_factor
        ):
            reasons.append(self._low_profit_factor_reason)
        if research_result.drawdown.max_drawdown_points > self.maximum_drawdown:
            reasons.append(self._high_drawdown_reason)
        if research_result.win_rate.win_rate < self.minimum_win_rate:
            reasons.append(self._low_win_rate_reason)
        return reasons

    def _status(self, reasons: tuple[str, ...]) -> str:
        if not reasons:
            return "APPROVED"
        if self._insufficient_trades_reason in reasons:
            return "INSUFFICIENT_TRADES"
        if self._low_profit_factor_reason in reasons:
            return "LOW_PROFIT_FACTOR"
        if self._high_drawdown_reason in reasons:
            return "HIGH_DRAWDOWN"
        if self._low_win_rate_reason in reasons:
            return "LOW_WIN_RATE"
        return "REJECTED"
