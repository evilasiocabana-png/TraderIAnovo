"""Strategy oficial da Alpha201."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha201.alpha201_config import Alpha201Config


SCORE_MULTIPLIER = 100
FORBIDDEN_REGIMES = {
    "RANGE",
    "RANGE_WEAK",
    "LOW_LIQUIDITY",
    "NO_TREND",
    "ERRATIC",
    "REVERSAL",
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
UP_TRENDS = {
    "UP",
    "UPTREND",
    "BULL",
    "BULLISH",
    "HIGH",
    "ALTA",
}
DOWN_TRENDS = {
    "DOWN",
    "DOWNTREND",
    "BEAR",
    "BEARISH",
    "LOW",
    "BAIXA",
}


@dataclass(frozen=True)
class Alpha201Strategy:
    """Aplica as regras de tendencia contextual Position Trade."""

    config: Alpha201Config
    nome: str = "alpha201_position_trend_contextual"

    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        """Gera StrategySignal a partir de contexto e features aprovadas."""
        rejection_reasons = self._rejection_reasons(market_context, feature_report)
        if rejection_reasons:
            return self._wait(rejection_reasons)

        trend = self._structural_trend(feature_report)
        persistence = self._feature_float(feature_report, "directional_persistence")
        momentum = self._feature_float(feature_report, "momentum")

        if trend == "UP" and persistence > 0 and momentum > 0:
            return self._signal(
                decision="BUY",
                confidence=market_context.confidence,
                reasons=[
                    "tendencia estrutural de alta qualificada",
                    "persistencia direcional positiva",
                    "momentum comprador sustentado",
                ],
            )

        if trend == "DOWN" and persistence < 0 and momentum < 0:
            return self._signal(
                decision="SELL",
                confidence=market_context.confidence,
                reasons=[
                    "tendencia estrutural de baixa qualificada",
                    "persistencia direcional negativa",
                    "momentum vendedor sustentado",
                ],
            )

        return self._wait(["gatilho de tendencia Position Trade nao confirmado"])

    def _rejection_reasons(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> list[str]:
        reasons: list[str] = []
        required_features = (
            "price",
            "structural_trend",
            "directional_persistence",
            "volume",
            "volatility",
            "momentum",
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
            reasons.append("regime proibido para Position Trade")
        if market_context.liquidity < self.config.minimum_volume:
            reasons.append("liquidez abaixo do minimo")
        if market_context.volatility < self.config.minimum_volatility:
            reasons.append("volatilidade abaixo do minimo")
        if market_context.confidence < self.config.minimum_confidence:
            reasons.append("confianca abaixo do minimo")
        if self._feature_float(feature_report, "volume") < self.config.minimum_volume:
            reasons.append("volume abaixo do minimo")
        if self._feature_float(feature_report, "volatility") < self.config.minimum_volatility:
            reasons.append("feature de volatilidade abaixo do minimo")
        if self._structural_trend(feature_report) is None:
            reasons.append("tendencia estrutural nao qualificada")
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

    def _structural_trend(self, feature_report: FeatureReport) -> str | None:
        raw_value = self._feature_value(feature_report, "structural_trend")
        value = str(raw_value).strip().upper()
        if value in UP_TRENDS:
            return "UP"
        if value in DOWN_TRENDS:
            return "DOWN"

        numeric_value = self._feature_float(feature_report, "structural_trend")
        if numeric_value is None:
            return None
        if numeric_value > 0:
            return "UP"
        if numeric_value < 0:
            return "DOWN"
        return None

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
