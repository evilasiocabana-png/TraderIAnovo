"""Pipeline oficial do Risk Lab."""

from __future__ import annotations

from dataclasses import dataclass, field

from market.context.market_context import MarketContext
from market.data.market_data_quality_engine import MarketDataQualityResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_research_report import Alpha001ResearchResult
from risk.risk_policy_engine import RiskPolicyEngine, RiskPolicyResult
from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreEngine


@dataclass(frozen=True)
class RiskPipeline:
    """Orquestra o fluxo do Risk Lab sem executar logica operacional."""

    score_engine: RiskScoreEngine = field(default_factory=RiskScoreEngine)
    policy_engine: RiskPolicyEngine = field(default_factory=RiskPolicyEngine)

    def run(
        self,
        profile: RiskProfile,
        market_context: MarketContext,
        data_quality: MarketDataQualityResult,
        research_result: Alpha001ResearchResult,
        drawdown_result: Alpha001DrawdownResult,
    ) -> RiskPolicyResult:
        """Executa score e politica na ordem oficial do Risk Lab."""
        score_result = self.score_engine.calculate(
            profile,
            market_context,
            data_quality,
            research_result,
            drawdown_result,
        )
        return self.policy_engine.evaluate(profile, score_result)
