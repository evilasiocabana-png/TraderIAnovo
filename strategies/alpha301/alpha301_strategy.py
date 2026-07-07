"""Strategy oficial da Alpha301."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha301.alpha301_config import Alpha301Config


SCORE_MULTIPLIER = 100
Z_SCORE_ENTRY_THRESHOLD = 1.0
FORBIDDEN_REGIMES = {
    "LOW_LIQUIDITY",
    "NO_RELATION",
    "BROKEN_RELATION",
    "ERRATIC",
    "UNCORRELATED",
}
BLOCKING_RISK_DECISIONS = {
    "BLOCK_RESEARCH",
    "BLOCK_PAPER",
}
BLOCKING_RESEARCH_STATUSES = {
    "FAILED",
    "REJECTED",
    "BLOCKED",
}


@dataclass(frozen=True)
class Alpha301Strategy:
    """Aplica as regras de valor relativo Long & Short."""

    config: Alpha301Config
    nome: str = "alpha301_long_short_relative_value"

    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        """Gera StrategySignal a partir de contexto e features aprovadas."""
        rejection_reasons = self._rejection_reasons(market_context, feature_report)
        if rejection_reasons:
            return self._wait(rejection_reasons)

        spread_zscore = self._feature_float(feature_report, "spread_zscore")

        if spread_zscore <= -Z_SCORE_ENTRY_THRESHOLD:
            return self._signal(
                decision="LONG",
                confidence=market_context.confidence,
                reasons=[
                    "instrumento principal relativamente descontado",
                    "z-score do spread abaixo do limite negativo",
                    "relacao estatistica validada",
                ],
            )

        if spread_zscore >= Z_SCORE_ENTRY_THRESHOLD:
            return self._signal(
                decision="SHORT",
                confidence=market_context.confidence,
                reasons=[
                    "instrumento principal relativamente esticado",
                    "z-score do spread acima do limite positivo",
                    "relacao estatistica validada",
                ],
            )

        return self._wait(["gatilho Long & Short nao confirmado"])

    def _rejection_reasons(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> list[str]:
        reasons: list[str] = []
        required_features = (
            "spread",
            "spread_zscore",
            "correlation",
            "primary_volume",
            "secondary_volume",
            "spread_volatility",
        )
        missing = [
            feature
            for feature in required_features
            if self._feature_value(feature_report, feature) is None
        ]
        if missing:
            reasons.append(f"features ausentes: {', '.join(missing)}")
            return reasons

        if market_context.regime.strip().upper() in FORBIDDEN_REGIMES:
            reasons.append("regime proibido para Long & Short")
        if market_context.liquidity < self.config.minimum_volume:
            reasons.append("liquidez agregada abaixo do minimo")
        if market_context.volatility > self.config.minimum_volatility:
            reasons.append("volatilidade do contexto acima do limite aceito")
        if market_context.confidence < self.config.minimum_confidence:
            reasons.append("confianca abaixo do minimo")
        if self._feature_float(feature_report, "primary_volume") < self.config.minimum_volume:
            reasons.append("volume do instrumento principal abaixo do minimo")
        if self._feature_float(feature_report, "secondary_volume") < self.config.minimum_volume:
            reasons.append("volume do instrumento secundario abaixo do minimo")
        if self._feature_float(feature_report, "spread_volatility") > self.config.minimum_volatility:
            reasons.append("volatilidade do spread acima do limite aceito")
        if self._feature_float(feature_report, "correlation") < self.config.minimum_confidence:
            reasons.append("correlacao abaixo do minimo")
        if self._data_quality_score(feature_report) < self.config.minimum_confidence:
            reasons.append("Data Lab abaixo do minimo")
        if self._decision_approval_score(market_context) < self.config.minimum_confidence:
            reasons.append("Decision Lab abaixo do minimo")
        if self._risk_decision(market_context) in BLOCKING_RISK_DECISIONS:
            reasons.append("Risk Lab bloqueou a pesquisa")
        if self._research_status(market_context) in BLOCKING_RESEARCH_STATUSES:
            reasons.append("Research Lab rejeitou o cenario")
        if self._research_confidence(market_context) < self.config.minimum_confidence:
            reasons.append("Research Lab abaixo do minimo")
        if self._reproducibility_score(market_context) < self.config.minimum_confidence:
            reasons.append("reprodutibilidade abaixo do minimo")
        return reasons

    def _feature_float(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> float | None:
        value = self._feature_value(feature_report, name)
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(converted):
            return None
        return converted

    def _feature_value(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> object | None:
        value = feature_report.calculated_values.get(name)
        if value is None:
            value = feature_report.calculated_values.get(name.upper())
        if value is None:
            value = feature_report.calculated_values.get(name.capitalize())
        return value

    def _data_quality_score(self, feature_report: FeatureReport) -> float:
        value = feature_report.calculated_values.get("data_quality_score", 1.0)
        return self._metadata_score(value)

    def _decision_approval_score(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("decision_approval_score", 1.0)
        return self._metadata_score(value)

    def _research_confidence(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("research_confidence", 1.0)
        return self._metadata_score(value)

    def _reproducibility_score(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("reproducibility_score", 1.0)
        return self._metadata_score(value)

    def _risk_decision(self, market_context: MarketContext) -> str:
        value = market_context.metadata.get("risk_policy_decision", "ALLOW")
        return str(value).strip().upper()

    def _research_status(self, market_context: MarketContext) -> str:
        value = market_context.metadata.get("research_validation_status", "PASSED")
        return str(value).strip().upper()

    def _metadata_score(self, value: object) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not isfinite(score):
            return 0.0
        return score

    def _signal(
        self,
        decision: str,
        confidence: float,
        reasons: list[str],
    ) -> StrategySignal:
        return StrategySignal(
            decision=decision,
            score=self._score(confidence),
            confidence=confidence,
            reasons=reasons,
        )

    def _wait(self, reasons: list[str]) -> StrategySignal:
        return StrategySignal(
            decision="WAIT",
            score=0,
            confidence=0.0,
            reasons=reasons,
        )

    def _score(self, confidence: float) -> int:
        if not isfinite(confidence):
            return 0
        normalized = min(max(confidence, 0.0), 1.0)
        return int(round(normalized * SCORE_MULTIPLIER))
