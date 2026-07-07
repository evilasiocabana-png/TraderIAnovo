"""Adaptador entre Decision Lab e DecisionPipeline."""

from dataclasses import dataclass, field
from math import isfinite

from core.decision_pipeline import DecisionPipeline
from decision.decision_assessment import DecisionAssessment
from decision.decision_quality_engine import DecisionQualityResult
from decision.decision_score_engine import DecisionScoreResult
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


@dataclass(frozen=True)
class DecisionPipelineAdapter:
    """Converte resultados do Decision Lab para o pipeline central."""

    pipeline: DecisionPipeline = field(default_factory=DecisionPipeline)

    def adapt(
        self,
        assessment: DecisionAssessment,
        score_result: DecisionScoreResult,
        quality_result: DecisionQualityResult,
    ) -> DecisionContext:
        """Retorna o DecisionContext usando apenas o contrato do pipeline."""
        strategy_signal = self._strategy_signal(
            assessment,
            score_result,
            quality_result,
        )
        market_snapshot = self._market_snapshot(assessment)
        risk_decision = self._risk_decision(assessment)

        return self.pipeline.processar(
            strategy_signal,
            market_snapshot,
            risk_decision,
        )

    def _strategy_signal(
        self,
        assessment: DecisionAssessment,
        score_result: DecisionScoreResult,
        quality_result: DecisionQualityResult,
    ) -> StrategySignal:
        return StrategySignal(
            decision=assessment.strategy_signal.decision,
            score=self._score(score_result.final_score),
            confidence=self._confidence(quality_result.confidence_score),
            reasons=list(assessment.strategy_signal.reasons),
        )

    def _market_snapshot(self, assessment: DecisionAssessment) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=str(assessment.metadata.get("symbol", "")),
            datetime=assessment.market_context.timestamp,
            regime=assessment.market_context.regime,
            volatility=assessment.market_context.volatility,
            liquidity=assessment.market_context.liquidity,
            trend_strength=self._metadata_float(assessment, "trend_strength"),
            market_dna_score=self._market_dna_score(assessment),
        )

    def _risk_decision(self, assessment: DecisionAssessment) -> RiskDecision:
        return assessment.risk_decision

    def _market_dna_score(self, assessment: DecisionAssessment) -> float:
        market_dna_score = assessment.market_context.market_dna.get(
            "market_dna_score",
            assessment.market_context.market_dna.get("similarity"),
        )
        if market_dna_score is None:
            return self._metadata_float(assessment, "market_dna_score")
        return self._float_or_zero(market_dna_score)

    def _metadata_float(
        self,
        assessment: DecisionAssessment,
        key: str,
    ) -> float:
        return self._float_or_zero(assessment.metadata.get(key, 0.0))

    def _score(self, value: float) -> int:
        if not isfinite(value):
            return 0
        return int(round(min(max(value, 0.0), 100.0)))

    def _confidence(self, value: float) -> float:
        if not isfinite(value):
            return 0.0
        normalized = min(max(value, 0.0), 100.0)
        return round(normalized / 100.0, 4)

    def _float_or_zero(self, value: object) -> float:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not isfinite(converted):
            return 0.0
        return converted
