"""Calculo quantitativo de score de risco."""

from dataclasses import dataclass
from math import isfinite

from market.context.market_context import MarketContext
from market.data.market_data_quality_engine import MarketDataQualityResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_research_report import Alpha001ResearchResult
from risk.risk_profile import RiskProfile


@dataclass(frozen=True)
class RiskScoreResult:
    """Resultado quantitativo de risco sem aprovacao operacional."""

    exposure_score: float
    drawdown_score: float
    volatility_score: float
    research_score: float
    final_risk_score: float


@dataclass(frozen=True)
class RiskScoreEngine:
    """Calcula score de risco sem aprovar ou executar ordens."""

    def calculate(
        self,
        profile: RiskProfile,
        market_context: MarketContext,
        data_quality: MarketDataQualityResult,
        research_result: Alpha001ResearchResult,
        drawdown_result: Alpha001DrawdownResult,
    ) -> RiskScoreResult:
        """Retorna scores normalizados em escala de 0 a 100."""
        exposure_score = self._exposure_score(profile)
        drawdown_score = self._drawdown_score(profile, drawdown_result)
        volatility_score = self._volatility_score(market_context)
        research_score = self._research_score(research_result)
        quality_factor = self._score(data_quality.quality_score) / 100.0
        final_risk_score = round(
            (
                exposure_score
                + drawdown_score
                + volatility_score
                + research_score
            )
            / 4
            * quality_factor,
            2,
        )

        return RiskScoreResult(
            exposure_score=exposure_score,
            drawdown_score=drawdown_score,
            volatility_score=volatility_score,
            research_score=research_score,
            final_risk_score=final_risk_score,
        )

    def _exposure_score(self, profile: RiskProfile) -> float:
        exposure_percent = self._ratio_or_percent(profile.max_exposure)
        contracts_penalty = max(profile.contracts - 1, 0) * 5.0
        return self._score(100.0 - exposure_percent - contracts_penalty)

    def _drawdown_score(
        self,
        profile: RiskProfile,
        drawdown_result: Alpha001DrawdownResult,
    ) -> float:
        limit_percent = self._ratio_or_percent(profile.max_drawdown_allowed)
        if limit_percent <= 0:
            return 0.0
        used = self._ratio_or_percent(drawdown_result.max_drawdown_percent)
        return self._score(100.0 - ((used / limit_percent) * 100.0))

    def _volatility_score(self, market_context: MarketContext) -> float:
        return self._score(100.0 - self._score(market_context.volatility))

    def _research_score(self, research_result: Alpha001ResearchResult) -> float:
        profit_factor_score = self._score(
            research_result.profit_factor.profit_factor * 50.0
        )
        win_rate_score = self._ratio_or_percent(research_result.win_rate.win_rate)
        expectancy_score = self._score(research_result.expectancy.expectancy)
        net_profit_score = self._score(research_result.profit.net_profit_points)
        return round(
            (
                profit_factor_score
                + win_rate_score
                + expectancy_score
                + net_profit_score
            )
            / 4,
            2,
        )

    def _ratio_or_percent(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value <= 0:
            return 0.0
        if value <= 1:
            return value * 100.0
        return value

    def _score(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        if value < 0:
            return 0.0
        if value > 100:
            return 100.0
        return round(value, 2)
